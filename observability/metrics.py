"""
Module de métriques Prometheus pour Nox API - Phase 2.2
Date: 13 août 2025

Implémente:
- Compteurs par endpoint HTTP
- Histogrammes de latence
- Métriques métier (sandbox, exécutions)
- Request ID correlation
- Export format Prometheus
"""

import os
import sys
import time
import uuid
from collections import Counter
from pathlib import Path

from fastapi import Request
from prometheus_client import Counter, Gauge, Histogram, Info
from starlette.middleware.base import BaseHTTPMiddleware


class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """Middleware pour collecte de métriques Prometheus"""

    def __init__(self, app):
        super().__init__(app)
        self.setup_metrics()

    def setup_metrics(self):
        """Initialise les métriques Prometheus"""

        # === MÉTRIQUES HTTP ===
        self.http_requests_total = Counter(
            "nox_api_http_requests_total",
            "Nombre total de requêtes HTTP",
            ["method", "endpoint", "status_code"],
        )

        self.http_request_duration_seconds = Histogram(
            "nox_api_http_request_duration_seconds",
            "Durée des requêtes HTTP en secondes",
            ["method", "endpoint"],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
        )

        # === MÉTRIQUES SÉCURITÉ ===
        self.rate_limit_hits = Counter(
            "nox_api_rate_limit_hits_total",
            "Nombre de hits de rate limiting",
            ["endpoint", "limit_type"],
        )

        self.auth_failures = Counter(
            "nox_api_auth_failures_total",
            "Nombre d'échecs d'authentification",
            ["reason"],
        )

        # === MÉTRIQUES MÉTIER ===
        self.code_executions_total = Counter(
            "nox_api_code_executions_total",
            "Nombre total d'exécutions de code",
            ["type", "status"],  # type: python/shell, status: success/error/timeout
        )

        self.code_execution_duration = Histogram(
            "nox_api_code_execution_duration_seconds",
            "Durée des exécutions de code",
            ["type"],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0],
        )

        self.file_operations_total = Counter(
            "nox_api_file_operations_total",
            "Opérations sur fichiers",
            ["operation"],  # upload, delete, read
        )

        # === MÉTRIQUES SYSTÈME ===
        self.sandbox_files_count = Gauge(
            "nox_api_sandbox_files_count", "Nombre de fichiers dans le sandbox"
        )

        self.sandbox_size_bytes = Gauge(
            "nox_api_sandbox_size_bytes", "Taille totale du sandbox en bytes"
        )

        self.active_tokens = Gauge(
            "nox_api_active_tokens_count", "Nombre de tokens actifs"
        )

        # === MÉTRIQUES APPLICATIVES ===
        self.api_info = Info("nox_api_build_info", "Informations de build de l'API")

        # Initialiser les infos de build
        self.api_info.info(
            {
                "version": "2.2.0",
                "phase": "2.2-observability",
                "build_date": time.strftime("%Y-%m-%d"),
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
            }
        )

        # État des métriques système
        self.last_metrics_update = 0
        self.metrics_update_interval = 30  # secondes

    def generate_request_id(self) -> str:
        """Génère un ID unique pour traçabilité"""
        return f"nox-{int(time.time())}-{uuid.uuid4().hex[:8]}"

    def update_system_metrics(self):
        """Met à jour les métriques système (appelé périodiquement)"""
        current_time = time.time()
        if current_time - self.last_metrics_update < self.metrics_update_interval:
            return

        try:
            # Métriques sandbox
            sandbox_path = Path(os.getenv("NOX_SANDBOX", "/home/nox/nox/sandbox"))
            if sandbox_path.exists():
                files = list(sandbox_path.rglob("*"))
                file_count = len([f for f in files if f.is_file()])
                total_size = sum(f.stat().st_size for f in files if f.is_file())

                self.sandbox_files_count.set(file_count)
                self.sandbox_size_bytes.set(total_size)

            # Mise à jour du timestamp
            self.last_metrics_update = current_time

        except Exception as e:
            # Log error but don't break the app
            print(f"Error updating system metrics: {e}")

    def track_code_execution(
        self, execution_type: str, duration: float, status: str, request_id: str
    ):
        """Track une exécution de code"""
        self.code_executions_total.labels(type=execution_type, status=status).inc()

        self.code_execution_duration.labels(type=execution_type).observe(duration)

        # Log structuré pour corrélation
        print(
            f"CODE_EXEC request_id={request_id} type={execution_type} "
            f"duration={duration:.3f}s status={status}"
        )

    def track_file_operation(self, operation: str, request_id: str):
        """Track une opération fichier"""
        self.file_operations_total.labels(operation=operation).inc()
        print(f"FILE_OP request_id={request_id} operation={operation}")

    def track_rate_limit_hit(self, endpoint: str, limit_type: str, request_id: str):
        """Track un hit de rate limiting"""
        self.rate_limit_hits.labels(endpoint=endpoint, limit_type=limit_type).inc()
        print(
            f"RATE_LIMIT request_id={request_id} endpoint={endpoint} type={limit_type}"
        )

    def track_auth_failure(self, reason: str, request_id: str):
        """Track un échec d'authentification"""
        self.auth_failures.labels(reason=reason).inc()
        print(f"AUTH_FAIL request_id={request_id} reason={reason}")

    async def dispatch(self, request: Request, call_next):
        """Point d'entrée principal du middleware de métriques"""

        # Génération request_id pour corrélation
        request_id = self.generate_request_id()
        request.state.request_id = request_id

        # Ajout header de corrélation
        start_time = time.time()
        method = request.method
        endpoint = str(request.url.path)

        # Log de début de requête
        print(
            f"REQUEST_START request_id={request_id} method={method} endpoint={endpoint}"
        )

        try:
            # Mise à jour métriques système périodique
            self.update_system_metrics()

            # Traitement de la requête
            response = await call_next(request)

            # Métriques de fin
            duration = time.time() - start_time
            status_code = str(response.status_code)

            # Enregistrement métriques HTTP
            self.http_requests_total.labels(
                method=method, endpoint=endpoint, status_code=status_code
            ).inc()

            self.http_request_duration_seconds.labels(
                method=method, endpoint=endpoint
            ).observe(duration)

            # Ajout du request_id en header de réponse
            response.headers["X-Request-ID"] = request_id

            # Log de fin de requête
            print(
                f"REQUEST_END request_id={request_id} status={status_code} "
                f"duration={duration:.3f}s"
            )

            return response

        except Exception as e:
            # Métriques d'erreur
            duration = time.time() - start_time
            self.http_requests_total.labels(
                method=method, endpoint=endpoint, status_code="500"
            ).inc()

            self.http_request_duration_seconds.labels(
                method=method, endpoint=endpoint
            ).observe(duration)

            print(
                f"REQUEST_ERROR request_id={request_id} error={str(e)} "
                f"duration={duration:.3f}s"
            )

            raise


# Instance globale pour utilisation dans l'API
_metrics_collector = None


def get_metrics_collector():
    """Récupère l'instance globale du collecteur de métriques"""
    return _metrics_collector


def set_metrics_collector(collector):
    """Définit l'instance globale du collecteur de métriques"""
    global _metrics_collector
    _metrics_collector = collector


# Instance globale initialisée
try:
    _metrics_collector = PrometheusMetricsMiddleware(None)
except:
    _metrics_collector = None
