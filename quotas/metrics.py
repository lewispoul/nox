"""
Prometheus metrics for quota monitoring
"""

import os

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

# Créer un registry custom pour éviter les conflits
quota_registry = CollectorRegistry()

# Métriques pour les quotas utilisateur
quota_violations = Counter(
    "nox_quota_violations_total",
    "Total number of quota violations",
    ["user_id", "quota_type"],
    registry=quota_registry,
)

quota_usage_ratio = Gauge(
    "nox_quota_usage_ratio",
    "Current quota usage ratio (0.0 to 1.0)",
    ["user_id", "quota_type"],
    registry=quota_registry,
)

quota_limits = Gauge(
    "nox_quota_limits",
    "Current quota limits per user",
    ["user_id", "quota_type"],
    registry=quota_registry,
)

quota_current_usage = Gauge(
    "nox_quota_current_usage",
    "Current usage per user",
    ["user_id", "quota_type"],
    registry=quota_registry,
)

# Métriques pour les requêtes par utilisateur
user_requests_total = Counter(
    "nox_user_requests_total",
    "Total HTTP requests per user",
    ["user_id", "endpoint", "status_code"],
    registry=quota_registry,
)

user_request_duration = Histogram(
    "nox_user_request_duration_seconds",
    "HTTP request duration per user",
    ["user_id", "endpoint"],
    registry=quota_registry,
)

# Métriques pour l'usage système par utilisateur
user_cpu_seconds_total = Counter(
    "nox_user_cpu_seconds_total",
    "Total CPU seconds consumed per user",
    ["user_id"],
    registry=quota_registry,
)

user_memory_peak_mb = Gauge(
    "nox_user_memory_peak_mb",
    "Peak memory usage in MB per user",
    ["user_id"],
    registry=quota_registry,
)

user_storage_mb = Gauge(
    "nox_user_storage_mb",
    "Current storage usage in MB per user",
    ["user_id"],
    registry=quota_registry,
)

user_files_count = Gauge(
    "nox_user_files_count",
    "Current number of files per user",
    ["user_id"],
    registry=quota_registry,
)

# Métriques d'alertes
quota_near_limit = Gauge(
    "nox_quota_near_limit",
    "Users near quota limit (1=true, 0=false)",
    ["user_id", "quota_type"],
    registry=quota_registry,
)

quota_exceeded = Gauge(
    "nox_quota_exceeded",
    "Users who exceeded quota (1=true, 0=false)",
    ["user_id", "quota_type"],
    registry=quota_registry,
)


class QuotaMetricsCollector:
    """Collecteur de métriques pour les quotas utilisateur"""

    def __init__(self):
        self.enabled = os.getenv("NOX_QUOTAS_ENABLED", "0") == "1"

    def record_request(
        self, user_id: str, endpoint: str, status_code: int, duration: float
    ):
        """Enregistre une requête HTTP"""
        if not self.enabled:
            return

        user_requests_total.labels(
            user_id=user_id, endpoint=endpoint, status_code=str(status_code)
        ).inc()

        user_request_duration.labels(user_id=user_id, endpoint=endpoint).observe(
            duration
        )

    def record_quota_violation(self, user_id: str, quota_type: str):
        """Enregistre une violation de quota"""
        if not self.enabled:
            return

        quota_violations.labels(user_id=user_id, quota_type=quota_type).inc()

        # Marquer comme dépassé
        quota_exceeded.labels(user_id=user_id, quota_type=quota_type).set(1)

    def update_quota_usage(
        self, user_id: str, quota_type: str, current: int, limit: int
    ):
        """Met à jour les métriques d'usage de quota"""
        if not self.enabled:
            return

        ratio = current / max(limit, 1)  # Éviter division par zéro

        quota_current_usage.labels(user_id=user_id, quota_type=quota_type).set(current)

        quota_limits.labels(user_id=user_id, quota_type=quota_type).set(limit)

        quota_usage_ratio.labels(user_id=user_id, quota_type=quota_type).set(ratio)

        # Alertes de seuil
        quota_near_limit.labels(user_id=user_id, quota_type=quota_type).set(
            1 if ratio >= 0.8 else 0
        )

        quota_exceeded.labels(user_id=user_id, quota_type=quota_type).set(
            1 if ratio >= 1.0 else 0
        )

    def record_cpu_usage(self, user_id: str, cpu_seconds: float):
        """Enregistre l'usage CPU"""
        if not self.enabled:
            return

        user_cpu_seconds_total.labels(user_id=user_id).inc(cpu_seconds)

    def update_memory_peak(self, user_id: str, memory_mb: int):
        """Met à jour le pic de mémoire"""
        if not self.enabled:
            return

        user_memory_peak_mb.labels(user_id=user_id).set(memory_mb)

    def update_storage_usage(self, user_id: str, storage_mb: int):
        """Met à jour l'usage de stockage"""
        if not self.enabled:
            return

        user_storage_mb.labels(user_id=user_id).set(storage_mb)

    def update_files_count(self, user_id: str, files_count: int):
        """Met à jour le nombre de fichiers"""
        if not self.enabled:
            return

        user_files_count.labels(user_id=user_id).set(files_count)

    def clear_user_metrics(self, user_id: str):
        """Efface toutes les métriques pour un utilisateur (quand supprimé)"""
        if not self.enabled:
            return

        # Note: Prometheus ne permet pas vraiment d'effacer les métriques
        # On peut seulement les mettre à zéro
        quota_types = [
            "req_hour",
            "req_day",
            "cpu_seconds",
            "mem_mb",
            "storage_mb",
            "files_max",
        ]

        for quota_type in quota_types:
            quota_usage_ratio.labels(user_id=user_id, quota_type=quota_type).set(0)
            quota_current_usage.labels(user_id=user_id, quota_type=quota_type).set(0)
            quota_limits.labels(user_id=user_id, quota_type=quota_type).set(0)
            quota_near_limit.labels(user_id=user_id, quota_type=quota_type).set(0)
            quota_exceeded.labels(user_id=user_id, quota_type=quota_type).set(0)


# Instance globale
quota_metrics = QuotaMetricsCollector()


def get_quota_metrics_output() -> str:
    """Génère la sortie des métriques au format Prometheus"""
    from prometheus_client import generate_latest

    return generate_latest(quota_registry).decode("utf-8")
