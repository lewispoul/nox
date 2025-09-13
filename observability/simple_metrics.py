"""
Module de métriques Prometheus simplifié pour Nox API - Phase 2.2
Date: 13 août 2025

Version simplifiée sans middleware complexe pour éviter les conflits
"""

import os
import sys
import time
import uuid
from pathlib import Path

from prometheus_client import Counter, Gauge, Histogram, Info, generate_latest

# === MÉTRIQUES GLOBALES ===

# Métriques HTTP
http_requests_total = Counter(
    "nox_api_http_requests_total",
    "Nombre total de requêtes HTTP",
    ["method", "endpoint", "status_code"],
)

http_request_duration_seconds = Histogram(
    "nox_api_http_request_duration_seconds",
    "Durée des requêtes HTTP en secondes",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# Métriques sécurité
rate_limit_hits = Counter(
    "nox_api_rate_limit_hits_total",
    "Nombre de hits de rate limiting",
    ["endpoint", "limit_type"],
)

auth_failures = Counter(
    "nox_api_auth_failures_total", "Nombre d'échecs d'authentification", ["reason"]
)

# Métriques métier
code_executions_total = Counter(
    "nox_api_code_executions_total",
    "Nombre total d'exécutions de code",
    ["type", "status"],  # type: python/shell, status: success/error/timeout
)

code_execution_duration = Histogram(
    "nox_api_code_execution_duration_seconds",
    "Durée des exécutions de code",
    ["type"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0],
)

file_operations_total = Counter(
    "nox_api_file_operations_total",
    "Opérations sur fichiers",
    ["operation"],  # upload, delete, read
)

# Métriques système
sandbox_files_count = Gauge(
    "nox_api_sandbox_files_count", "Nombre de fichiers dans le sandbox"
)

sandbox_size_bytes = Gauge(
    "nox_api_sandbox_size_bytes", "Taille totale du sandbox en bytes"
)

# Info de build
api_info = Info("nox_api_build_info", "Informations de build de l'API")

# Initialiser les infos de build
api_info.info(
    {
        "version": "2.2.0",
        "phase": "2.2-observability",
        "build_date": time.strftime("%Y-%m-%d"),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
    }
)

# === FONCTIONS HELPER ===


def generate_request_id() -> str:
    """Génère un ID unique pour traçabilité"""
    return str(uuid.uuid4())[:8]


def generate_metrics() -> str:
    """Génère les métriques Prometheus au format texte"""
    from prometheus_client import REGISTRY, generate_latest

    return generate_latest(REGISTRY)


def update_system_metrics():
    """Met à jour les métriques système"""
    try:
        sandbox_path = Path(os.getenv("NOX_SANDBOX", "/home/nox/nox/sandbox"))
        if sandbox_path.exists():
            files = list(sandbox_path.rglob("*"))
            file_count = len([f for f in files if f.is_file()])
            total_size = sum(f.stat().st_size for f in files if f.is_file())

            sandbox_files_count.set(file_count)
            sandbox_size_bytes.set(total_size)
    except Exception as e:
        print(f"Error updating system metrics: {e}")


def track_http_request(method: str, endpoint: str, status_code: int, duration: float):
    """Track une requête HTTP"""
    http_requests_total.labels(
        method=method, endpoint=endpoint, status_code=str(status_code)
    ).inc()

    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(
        duration
    )


def track_code_execution(
    execution_type: str, duration: float, status: str, request_id: str
):
    """Track une exécution de code"""
    code_executions_total.labels(type=execution_type, status=status).inc()

    code_execution_duration.labels(type=execution_type).observe(duration)

    print(
        f"CODE_EXEC request_id={request_id} type={execution_type} "
        f"duration={duration:.3f}s status={status}"
    )


def track_file_operation(operation: str, request_id: str):
    """Track une opération fichier"""
    file_operations_total.labels(operation=operation).inc()
    print(f"FILE_OP request_id={request_id} operation={operation}")


def track_rate_limit_hit(endpoint: str, limit_type: str, request_id: str):
    """Track un hit de rate limiting"""
    rate_limit_hits.labels(endpoint=endpoint, limit_type=limit_type).inc()
    print(f"RATE_LIMIT request_id={request_id} endpoint={endpoint} type={limit_type}")


def track_auth_failure(reason: str, request_id: str):
    """Track un échec d'authentification"""
    auth_failures.labels(reason=reason).inc()
    print(f"AUTH_FAIL request_id={request_id} reason={reason}")


def get_prometheus_metrics():
    """Récupère les métriques au format Prometheus"""
    update_system_metrics()  # Mise à jour avant export
    return generate_latest()
