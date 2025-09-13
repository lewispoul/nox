"""
Database operations for quota management
"""

import os
import uuid
from typing import Any, Dict, List, Optional

import asyncpg

from .models import QuotaViolation, UserQuota, UserUsage


class QuotaDatabase:
    """Gestionnaire de base de données pour les quotas"""

    def __init__(self, connection_string: Optional[str] = None):
        self.connection_string = connection_string or self._build_connection_string()

    def _build_connection_string(self) -> str:
        """Construit la chaîne de connexion PostgreSQL"""
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        database = os.getenv("POSTGRES_DB", "noxdb")
        user = os.getenv("POSTGRES_USER", "noxuser")
        password = os.getenv("POSTGRES_PASSWORD", "test_password_123")

        return f"postgresql://{user}:{password}@{host}:{port}/{database}"

    async def connect(self):
        """Crée une connexion à la base de données"""
        return await asyncpg.connect(self.connection_string)

    async def get_user_by_oauth_id(self, oauth_id: str) -> Optional[Dict[str, Any]]:
        """Récupère un utilisateur par son oauth_id"""
        conn = await self.connect()
        try:
            row = await conn.fetchrow(
                """
                SELECT id, email, oauth_provider, oauth_id
                FROM users WHERE oauth_id = $1
            """,
                oauth_id,
            )

            if row:
                return {
                    "id": row["id"],
                    "email": row["email"],
                    "oauth_provider": row["oauth_provider"],
                    "oauth_id": row["oauth_id"],
                }
            return None
        except Exception as e:
            print(f"Erreur récupération utilisateur par oauth_id {oauth_id}: {e}")
            return None
        finally:
            await conn.close()

    # Gestion des quotas utilisateur
    async def get_user_quotas(self, user_id: str) -> Optional[UserQuota]:
        """Récupère les quotas d'un utilisateur"""
        conn = await self.connect()
        try:
            row = await conn.fetchrow(
                """
                SELECT quota_req_hour, quota_req_day, quota_cpu_seconds,
                       quota_mem_mb, quota_storage_mb, quota_files_max
                FROM users WHERE id = $1
            """,
                uuid.UUID(user_id),
            )

            if row:
                return UserQuota(
                    user_id=user_id,
                    quota_req_hour=row["quota_req_hour"],
                    quota_req_day=row["quota_req_day"],
                    quota_cpu_seconds=row["quota_cpu_seconds"],
                    quota_mem_mb=row["quota_mem_mb"],
                    quota_storage_mb=row["quota_storage_mb"],
                    quota_files_max=row["quota_files_max"],
                )
            return None
        finally:
            await conn.close()

    async def update_user_quotas(self, user_id: str, quotas: UserQuota) -> bool:
        """Met à jour les quotas d'un utilisateur"""
        conn = await self.connect()
        try:
            result = await conn.execute(
                """
                UPDATE users SET
                    quota_req_hour = $2,
                    quota_req_day = $3,
                    quota_cpu_seconds = $4,
                    quota_mem_mb = $5,
                    quota_storage_mb = $6,
                    quota_files_max = $7
                WHERE id = $1
            """,
                uuid.UUID(user_id),
                quotas.quota_req_hour,
                quotas.quota_req_day,
                quotas.quota_cpu_seconds,
                quotas.quota_mem_mb,
                quotas.quota_storage_mb,
                quotas.quota_files_max,
            )
            return result != "UPDATE 0"
        finally:
            await conn.close()

    # Gestion de l'usage utilisateur
    async def get_user_usage(self, user_id: str) -> Optional[UserUsage]:
        """Récupère l'usage actuel d'un utilisateur"""
        conn = await self.connect()
        try:
            row = await conn.fetchrow(
                """
                SELECT user_id, req_hour, req_day, cpu_seconds,
                       mem_peak_mb, storage_mb, files_count, updated_at
                FROM user_usage WHERE user_id = $1
            """,
                uuid.UUID(user_id),
            )

            if row:
                return UserUsage(
                    user_id=str(row["user_id"]),
                    req_hour=row["req_hour"],
                    req_day=row["req_day"],
                    cpu_seconds=row["cpu_seconds"],
                    mem_peak_mb=row["mem_peak_mb"],
                    storage_mb=row["storage_mb"],
                    files_count=row["files_count"],
                    updated_at=row["updated_at"],
                )
            return None
        finally:
            await conn.close()

    async def create_or_update_usage(self, user_id: str, usage: UserUsage):
        """Crée ou met à jour l'usage utilisateur"""
        conn = await self.connect()
        try:
            await conn.execute(
                """
                INSERT INTO user_usage (
                    user_id, req_hour, req_day, cpu_seconds,
                    mem_peak_mb, storage_mb, files_count, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (user_id) DO UPDATE SET
                    req_hour = EXCLUDED.req_hour,
                    req_day = EXCLUDED.req_day,
                    cpu_seconds = EXCLUDED.cpu_seconds,
                    mem_peak_mb = EXCLUDED.mem_peak_mb,
                    storage_mb = EXCLUDED.storage_mb,
                    files_count = EXCLUDED.files_count,
                    updated_at = EXCLUDED.updated_at
            """,
                uuid.UUID(user_id),
                usage.req_hour,
                usage.req_day,
                usage.cpu_seconds,
                usage.mem_peak_mb,
                usage.storage_mb,
                usage.files_count,
                usage.updated_at,
            )
        finally:
            await conn.close()

    async def increment_request_counters(self, user_id: str):
        """Incrémente les compteurs de requêtes horaire et journalier"""
        conn = await self.connect()
        try:
            await conn.execute(
                """
                INSERT INTO user_usage (user_id, req_hour, req_day, updated_at)
                VALUES ($1, 1, 1, NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    req_hour = user_usage.req_hour + 1,
                    req_day = user_usage.req_day + 1,
                    updated_at = NOW()
            """,
                uuid.UUID(user_id),
            )
        finally:
            await conn.close()

    async def add_cpu_usage(self, user_id: str, cpu_seconds: float):
        """Ajoute de l'usage CPU à un utilisateur"""
        conn = await self.connect()
        try:
            await conn.execute(
                """
                INSERT INTO user_usage (user_id, cpu_seconds, updated_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    cpu_seconds = user_usage.cpu_seconds + $2,
                    updated_at = NOW()
            """,
                uuid.UUID(user_id),
                int(cpu_seconds),
            )
        finally:
            await conn.close()

    async def update_memory_peak(self, user_id: str, memory_mb: int):
        """Met à jour le pic de mémoire si plus élevé"""
        conn = await self.connect()
        try:
            await conn.execute(
                """
                INSERT INTO user_usage (user_id, mem_peak_mb, updated_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    mem_peak_mb = GREATEST(user_usage.mem_peak_mb, $2),
                    updated_at = NOW()
            """,
                uuid.UUID(user_id),
                memory_mb,
            )
        finally:
            await conn.close()

    async def update_storage_usage(
        self, user_id: str, storage_mb: int, files_count: int
    ):
        """Met à jour l'usage de stockage et le nombre de fichiers"""
        conn = await self.connect()
        try:
            await conn.execute(
                """
                INSERT INTO user_usage (user_id, storage_mb, files_count, updated_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    storage_mb = $2,
                    files_count = $3,
                    updated_at = NOW()
            """,
                uuid.UUID(user_id),
                storage_mb,
                files_count,
            )
        finally:
            await conn.close()

    # Gestion des violations de quotas
    async def record_quota_violation(
        self, user_id: str, reason: str, detail: Dict[str, Any]
    ):
        """Enregistre une violation de quota"""
        import json

        conn = await self.connect()
        try:
            violation_id = uuid.uuid4()
            await conn.execute(
                """
                INSERT INTO quota_violations (id, user_id, reason, detail, created_at)
                VALUES ($1, $2, $3, $4::jsonb, NOW())
            """,
                violation_id,
                uuid.UUID(user_id),
                reason,
                json.dumps(detail),
            )
        finally:
            await conn.close()

    async def get_quota_violations(
        self, user_id: Optional[str] = None, hours: int = 24, limit: int = 100
    ) -> List[QuotaViolation]:
        """Récupère les violations récentes"""
        conn = await self.connect()
        try:
            if user_id:
                rows = await conn.fetch(
                    """
                    SELECT id, user_id, reason, detail, created_at
                    FROM quota_violations
                    WHERE user_id = $1 AND created_at >= NOW() - INTERVAL '%d hours'
                    ORDER BY created_at DESC
                    LIMIT $2
                """
                    % hours,
                    uuid.UUID(user_id),
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT id, user_id, reason, detail, created_at
                    FROM quota_violations
                    WHERE created_at >= NOW() - INTERVAL '%d hours'
                    ORDER BY created_at DESC
                    LIMIT $1
                """
                    % hours,
                    limit,
                )

            violations = []
            for row in rows:
                # Désérialiser le JSON si c'est une chaîne
                detail = row["detail"] or {}
                if isinstance(detail, str):
                    import json

                    detail = json.loads(detail)

                violations.append(
                    QuotaViolation(
                        id=str(row["id"]),
                        user_id=str(row["user_id"]),
                        reason=row["reason"],
                        detail=detail,
                        created_at=row["created_at"],
                    )
                )

            return violations
        finally:
            await conn.close()

    # Nettoyage périodique
    async def reset_hourly_counters(self):
        """Remet à zéro les compteurs horaires (à appeler chaque heure)"""
        conn = await self.connect()
        try:
            result = await conn.execute(
                """
                UPDATE user_usage SET req_hour = 0, updated_at = NOW()
            """
            )
            return result
        finally:
            await conn.close()

    async def reset_daily_counters(self):
        """Remet à zéro les compteurs journaliers (à appeler chaque jour)"""
        conn = await self.connect()
        try:
            result = await conn.execute(
                """
                UPDATE user_usage SET req_day = 0, updated_at = NOW()
            """
            )
            return result
        finally:
            await conn.close()

    async def cleanup_old_violations(self, days: int = 30):
        """Nettoie les anciennes violations"""
        conn = await self.connect()
        try:
            result = await conn.execute(
                """
                DELETE FROM quota_violations 
                WHERE created_at < NOW() - INTERVAL '%d days'
            """
                % days
            )
            return result
        finally:
            await conn.close()

    # Statistiques
    async def get_usage_statistics(self) -> Dict[str, Any]:
        """Récupère les statistiques globales d'usage"""
        conn = await self.connect()
        try:
            stats = await conn.fetchrow(
                """
                SELECT 
                    COUNT(*) as total_users,
                    SUM(req_hour) as total_req_hour,
                    SUM(req_day) as total_req_day,
                    SUM(cpu_seconds) as total_cpu_seconds,
                    AVG(mem_peak_mb) as avg_mem_peak_mb,
                    SUM(storage_mb) as total_storage_mb,
                    SUM(files_count) as total_files_count
                FROM user_usage
            """
            )

            violations_count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM quota_violations
                WHERE created_at >= NOW() - INTERVAL '24 hours'
            """
            )

            return {
                "total_users": stats["total_users"],
                "total_req_hour": stats["total_req_hour"],
                "total_req_day": stats["total_req_day"],
                "total_cpu_seconds": stats["total_cpu_seconds"],
                "avg_mem_peak_mb": (
                    float(stats["avg_mem_peak_mb"]) if stats["avg_mem_peak_mb"] else 0
                ),
                "total_storage_mb": stats["total_storage_mb"],
                "total_files_count": stats["total_files_count"],
                "violations_last_24h": violations_count,
            }
        finally:
            await conn.close()
