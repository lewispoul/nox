"""
Middleware FastAPI pour Rate Limiting et Audit - Nox API Phase 2.1
Date: 13 août 2025

Ce middleware implémente:
- Rate limiting par IP et par token
- Quotas d'usage
- Audit logging avec signature HMAC
- Validation des politiques de sécurité
"""

import hashlib
import hmac
import json
import logging
import os
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Dict

import yaml
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Configuration globale
POLICIES_FILE = Path(__file__).parent.parent / "policy" / "policies.yaml"
AUDIT_KEY = os.getenv("NOX_AUDIT_KEY", "nox-default-audit-key-change-me")


class RateLimitAndPolicyMiddleware(BaseHTTPMiddleware):
    """Middleware pour Rate Limiting, Quotas et Audit de sécurité"""

    def __init__(self, app, policies_file: str = None):
        super().__init__(app)
        self.policies_file = policies_file or POLICIES_FILE
        self.policies = self.load_policies()

        # Stockage en mémoire des compteurs (en production, utiliser Redis)
        self.ip_counters = defaultdict(lambda: deque())
        self.token_counters = defaultdict(lambda: deque())
        self.daily_quotas = defaultdict(
            lambda: {"cpu_seconds": 0, "requests": 0, "last_reset": time.time()}
        )

        # Configuration des logs d'audit
        self.setup_audit_logging()

    def load_policies(self) -> Dict[str, Any]:
        """Charge la configuration des politiques depuis le fichier YAML"""
        try:
            if self.policies_file.exists():
                with open(self.policies_file, "r", encoding="utf-8") as f:
                    policies = yaml.safe_load(f)
                    return policies
            else:
                # Politiques par défaut si fichier manquant
                return self.get_default_policies()
        except Exception as e:
            logging.error(f"Erreur chargement politiques: {e}")
            return self.get_default_policies()

    def get_default_policies(self) -> Dict[str, Any]:
        """Politiques de sécurité par défaut"""
        return {
            "rate_limits": {
                "per_ip": {"requests_per_minute": 60, "burst_size": 10},
                "per_token": {"requests_per_minute": 100, "burst_size": 20},
                "endpoints": {
                    "/run_py": {"requests_per_minute": 30},
                    "/run_sh": {"requests_per_minute": 30},
                    "/put": {"requests_per_minute": 50},
                    "/api/backup": {"requests_per_minute": 5},
                },
            },
            "quotas": {
                "default": {
                    "daily_cpu_seconds": 3600,
                    "max_run_duration": 120,
                    "max_upload_size_mb": 50,
                    "max_files": 1000,
                }
            },
            "shell_policy": {
                "mode": "blacklist",
                "forbidden_commands": [
                    "rm",
                    "reboot",
                    "shutdown",
                    "mkfs",
                    "dd",
                    "mount",
                    "umount",
                    "kill",
                    "pkill",
                    "sudo",
                    "su",
                    "passwd",
                    "chown",
                    "chmod",
                ],
            },
            "audit": {
                "enabled": True,
                "log_file": "/home/lppoulin/nox-api-src/logs/audit.jsonl",
            },
        }

    def setup_audit_logging(self):
        """Configure le système de logs d'audit"""
        audit_config = self.policies.get("audit", {})
        if not audit_config.get("enabled", True):
            self.audit_logger = None
            return

        log_file = audit_config.get(
            "log_file", "/home/lppoulin/nox-api-src/logs/audit.jsonl"
        )
        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # Configuration du logger d'audit
        self.audit_logger = logging.getLogger("nox_audit")
        self.audit_logger.setLevel(logging.INFO)

        # Handler pour fichier JSONL
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter("%(message)s"))
        self.audit_logger.addHandler(handler)

    def check_rate_limit(self, client_ip: str, token: str, endpoint: str) -> bool:
        """Vérifie les limites de taux de requêtes"""
        current_time = time.time()

        # Nettoyage des anciens compteurs (> 1 minute)
        self.cleanup_old_counters(current_time)

        # Vérification limite par IP
        ip_limit = self.policies["rate_limits"]["per_ip"]
        ip_requests = len(self.ip_counters[client_ip])
        if ip_requests >= ip_limit["requests_per_minute"]:
            return False

        # Vérification limite par token
        if token:
            token_limit = self.policies["rate_limits"]["per_token"]
            token_requests = len(self.token_counters[token])
            if token_requests >= token_limit["requests_per_minute"]:
                return False

        # Vérification limite par endpoint spécifique
        endpoint_limits = self.policies["rate_limits"]["endpoints"]
        if endpoint in endpoint_limits:
            endpoint_limit = endpoint_limits[endpoint]["requests_per_minute"]
            endpoint_key = f"{client_ip}:{endpoint}"
            endpoint_requests = len(self.ip_counters[endpoint_key])
            if endpoint_requests >= endpoint_limit:
                return False

        # Ajouter la requête aux compteurs
        self.ip_counters[client_ip].append(current_time)
        if token:
            self.token_counters[token].append(current_time)
        if endpoint in endpoint_limits:
            self.ip_counters[f"{client_ip}:{endpoint}"].append(current_time)

        return True

    def cleanup_old_counters(self, current_time: float):
        """Nettoie les compteurs de requêtes anciennes (> 60s)"""
        cutoff_time = current_time - 60  # 1 minute

        # Nettoyage compteurs IP
        for ip, counter in self.ip_counters.items():
            while counter and counter[0] < cutoff_time:
                counter.popleft()

        # Nettoyage compteurs token
        for token, counter in self.token_counters.items():
            while counter and counter[0] < cutoff_time:
                counter.popleft()

    def check_quotas(self, token: str, endpoint: str) -> bool:
        """Vérifie les quotas d'usage quotidiens"""
        if not token:
            return True

        current_time = time.time()
        quota_data = self.daily_quotas[token]

        # Reset quotas si nouveau jour
        if current_time - quota_data["last_reset"] > 86400:  # 24h
            quota_data.update(
                {"cpu_seconds": 0, "requests": 0, "last_reset": current_time}
            )

        # Vérification quota de requêtes (simple compteur)
        quota_config = self.policies["quotas"]["default"]
        daily_request_limit = quota_config.get(
            "daily_requests", 10000
        )  # Limite par défaut

        if quota_data["requests"] >= daily_request_limit:
            return False

        # Incrémenter le compteur
        quota_data["requests"] += 1

        return True

    def validate_shell_command(self, command: str) -> bool:
        """Valide une commande shell selon les politiques"""
        shell_policy = self.policies.get("shell_policy", {})
        mode = shell_policy.get("mode", "blacklist")

        if not command.strip():
            return False

        # Extraire la première commande
        first_cmd = command.strip().split()[0] if command.strip() else ""

        if mode == "blacklist":
            forbidden = shell_policy.get("forbidden_commands", [])
            return first_cmd not in forbidden
        elif mode == "whitelist":
            allowed = shell_policy.get("allowed_commands", [])
            return first_cmd in allowed

        return True

    def create_audit_log(
        self,
        request: Request,
        response: Response,
        token: str,
        start_time: float,
        error: str = None,
    ):
        """Crée un log d'audit avec signature HMAC"""
        if not self.audit_logger:
            return

        execution_time = int((time.time() - start_time) * 1000)  # ms

        # Données d'audit
        audit_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
            "timestamp_unix": int(time.time()),
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
            "token_id": hashlib.sha256(
                token.encode() if token else b"anonymous"
            ).hexdigest()[:16],
            "method": request.method,
            "endpoint": str(request.url.path),
            "query_params": str(request.url.query) if request.url.query else None,
            "response_code": response.status_code if response else 0,
            "execution_time_ms": execution_time,
            "error_message": error,
        }

        # Signature HMAC pour l'intégrité
        audit_json = json.dumps(audit_data, sort_keys=True)
        signature = hmac.new(
            AUDIT_KEY.encode(), audit_json.encode(), hashlib.sha256
        ).hexdigest()

        audit_data["hmac_signature"] = signature

        # Log au format JSONL
        self.audit_logger.info(json.dumps(audit_data))

    async def dispatch(self, request: Request, call_next):
        """Point d'entrée principal du middleware"""
        start_time = time.time()
        client_ip = request.client.host if request.client else "unknown"
        endpoint = str(request.url.path)

        # Extraction du token Bearer
        auth_header = request.headers.get("authorization", "")
        token = (
            auth_header.replace("Bearer ", "").strip()
            if auth_header.startswith("Bearer ")
            else None
        )

        try:
            # 1. Vérification Rate Limiting
            if not self.check_rate_limit(client_ip, token, endpoint):
                response = Response(
                    content=json.dumps({"error": "Rate limit exceeded"}),
                    status_code=429,
                    headers={"Retry-After": "60", "Content-Type": "application/json"},
                )
                self.create_audit_log(
                    request, response, token, start_time, "rate_limit_exceeded"
                )
                return response

            # 2. Vérification Quotas
            if not self.check_quotas(token, endpoint):
                response = Response(
                    content=json.dumps({"error": "Daily quota exceeded"}),
                    status_code=429,
                    headers={"Content-Type": "application/json"},
                )
                self.create_audit_log(
                    request, response, token, start_time, "quota_exceeded"
                )
                return response

            # 3. Validation commandes shell (pour endpoint /run_sh)
            if endpoint == "/run_sh" and request.method == "POST":
                try:
                    body = await request.body()
                    if body:
                        data = json.loads(body.decode())
                        command = data.get("cmd", "")
                        if not self.validate_shell_command(command):
                            response = Response(
                                content=json.dumps({"error": "Forbidden command"}),
                                status_code=403,
                                headers={"Content-Type": "application/json"},
                            )
                            self.create_audit_log(
                                request,
                                response,
                                token,
                                start_time,
                                f"forbidden_command: {command}",
                            )
                            return response
                except Exception:
                    pass  # Si erreur parsing, laisser l'API gérer

            # 4. Traitement normal de la requête
            response = await call_next(request)

            # 5. Audit de la requête réussie
            self.create_audit_log(request, response, token, start_time)

            return response

        except Exception as e:
            # 6. Audit des erreurs
            error_response = Response(
                content=json.dumps({"error": "Internal server error"}),
                status_code=500,
                headers={"Content-Type": "application/json"},
            )
            self.create_audit_log(request, error_response, token, start_time, str(e))
            return error_response
