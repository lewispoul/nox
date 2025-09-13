"""
Quota models for advanced user limit management
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class QuotaType(str, Enum):
    """Types de quotas disponibles"""

    REQUESTS_HOUR = "req_hour"
    REQUESTS_DAY = "req_day"
    CPU_SECONDS = "cpu_seconds"
    MEMORY_MB = "mem_mb"
    STORAGE_MB = "storage_mb"
    FILES_MAX = "files_max"


class UserQuota(BaseModel):
    """Modèle des quotas utilisateur"""

    user_id: str
    quota_req_hour: Optional[int] = Field(default=100, description="Requêtes par heure")
    quota_req_day: Optional[int] = Field(default=1000, description="Requêtes par jour")
    quota_cpu_seconds: Optional[int] = Field(
        default=300, description="Secondes CPU max"
    )
    quota_mem_mb: Optional[int] = Field(default=512, description="Mémoire max en MB")
    quota_storage_mb: Optional[int] = Field(
        default=100, description="Stockage max en MB"
    )
    quota_files_max: Optional[int] = Field(
        default=50, description="Nombre max de fichiers"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "quota_req_hour": self.quota_req_hour,
            "quota_req_day": self.quota_req_day,
            "quota_cpu_seconds": self.quota_cpu_seconds,
            "quota_mem_mb": self.quota_mem_mb,
            "quota_storage_mb": self.quota_storage_mb,
            "quota_files_max": self.quota_files_max,
        }


class UserUsage(BaseModel):
    """Modèle d'usage utilisateur en temps réel"""

    user_id: str
    req_hour: int = Field(default=0, description="Requêtes dans la dernière heure")
    req_day: int = Field(default=0, description="Requêtes dans les 24h")
    cpu_seconds: int = Field(default=0, description="Temps CPU consommé (cumulé)")
    mem_peak_mb: int = Field(default=0, description="Pic de mémoire observé")
    storage_mb: int = Field(default=0, description="Espace disque utilisé")
    files_count: int = Field(default=0, description="Nombre de fichiers")
    updated_at: datetime = Field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "req_hour": self.req_hour,
            "req_day": self.req_day,
            "cpu_seconds": self.cpu_seconds,
            "mem_peak_mb": self.mem_peak_mb,
            "storage_mb": self.storage_mb,
            "files_count": self.files_count,
            "updated_at": self.updated_at.isoformat(),
        }


class QuotaViolation(BaseModel):
    """Modèle des violations de quotas"""

    id: str
    user_id: str
    reason: str = Field(description="Type de quota violé")
    detail: Dict[str, Any] = Field(
        default_factory=dict, description="Détails de la violation"
    )
    created_at: datetime = Field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "reason": self.reason,
            "detail": self.detail,
            "created_at": self.created_at.isoformat(),
        }


class QuotaCheckResult(BaseModel):
    """Résultat d'une vérification de quota"""

    allowed: bool
    quota_type: QuotaType
    current_usage: int
    limit: int
    percentage: float
    message: str

    def is_near_limit(self, threshold: float = 0.8) -> bool:
        """Vérifie si proche de la limite"""
        return self.percentage >= threshold

    def is_exceeded(self) -> bool:
        """Vérifie si la limite est dépassée"""
        return not self.allowed
