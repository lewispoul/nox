"""
Admin routes for quota management
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .database import QuotaDatabase
from .metrics import get_quota_metrics_output, quota_metrics
from .models import UserQuota

# Instance de base de données
quota_db = QuotaDatabase()

# Router pour les endpoints d'administration
admin_router = APIRouter(prefix="/quotas/admin", tags=["quotas-admin"])

# Router pour les endpoints utilisateur
user_router = APIRouter(prefix="/quotas", tags=["quotas"])


async def get_current_user_id(request: Request) -> str:
    """
    Extrait l'UUID utilisateur depuis le token Bearer.
    Utilise l'oauth_id pour trouver l'UUID dans la base de données.
    """
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token Bearer requis")

    token = auth_header.replace("Bearer ", "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Token vide")

    # Chercher l'utilisateur par oauth_id
    user = await quota_db.get_user_by_oauth_id(token)
    if not user:
        raise HTTPException(
            status_code=404, detail="Utilisateur non trouvé pour le token"
        )

    return str(user["id"])


@admin_router.get("/users/{user_id}/quotas", response_model=UserQuota)
async def get_user_quotas(user_id: str):
    """Récupère les quotas d'un utilisateur (admin seulement)"""
    quotas = await quota_db.get_user_quotas(user_id)
    if not quotas:
        raise HTTPException(status_code=404, detail="User quotas not found")
    return quotas


@admin_router.put("/users/{user_id}/quotas")
async def update_user_quotas(user_id: str, quotas: UserQuota):
    """Met à jour les quotas d'un utilisateur (admin seulement)"""
    quotas.user_id = user_id  # S'assurer que l'ID correspond

    success = await quota_db.update_user_quotas(user_id, quotas)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")

    # Mettre à jour les métriques Prometheus
    quota_metrics.update_quota_usage(
        user_id=user_id,
        quota_type="req_hour",
        current=0,  # On ne connaît pas l'usage actuel ici
        limit=quotas.quota_req_hour,
    )

    return {"message": "Quotas updated successfully", "quotas": quotas}


@admin_router.get("/violations")
async def get_quota_violations(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    hours: int = Query(24, description="Hours to look back"),
    limit: int = Query(100, description="Maximum number of violations to return"),
):
    """Récupère les violations de quotas récentes (admin seulement)"""
    violations = await quota_db.get_quota_violations(user_id, hours, limit)
    return {
        "violations": violations,
        "total": len(violations),
        "hours": hours,
        "user_id": user_id,
    }


@admin_router.get("/statistics")
async def get_usage_statistics():
    """Récupère les statistiques globales d'usage (admin seulement)"""
    stats = await quota_db.get_usage_statistics()
    return {"statistics": stats, "timestamp": datetime.now().isoformat()}


@admin_router.post("/reset/hourly")
async def reset_hourly_counters():
    """Remet à zéro les compteurs horaires pour tous les utilisateurs (admin seulement)"""
    result = await quota_db.reset_hourly_counters()
    return {"message": "Hourly counters reset", "affected_rows": result}


@admin_router.post("/reset/daily")
async def reset_daily_counters():
    """Remet à zéro les compteurs journaliers pour tous les utilisateurs (admin seulement)"""
    result = await quota_db.reset_daily_counters()
    return {"message": "Daily counters reset", "affected_rows": result}


@admin_router.delete("/violations/cleanup")
async def cleanup_old_violations(
    days: int = Query(30, description="Delete violations older than this many days")
):
    """Nettoie les anciennes violations (admin seulement)"""
    result = await quota_db.cleanup_old_violations(days)
    return {
        "message": "Old violations cleaned up",
        "days": days,
        "affected_rows": result,
    }


# Endpoints utilisateur (accès avec authentification normale)
@user_router.get("/my/quotas")
async def get_my_quotas(current_user_id: str = Depends(get_current_user_id)):
    """Récupère ses propres quotas"""
    quotas = await quota_db.get_user_quotas(current_user_id)
    if not quotas:
        raise HTTPException(status_code=404, detail="Your quotas not found")
    return quotas.to_dict()


@user_router.get("/my/usage")
async def get_my_usage(current_user_id: str = Depends(get_current_user_id)):
    """Récupère son propre usage"""
    usage = await quota_db.get_user_usage(current_user_id)
    if not usage:
        # Créer un usage vide si pas trouvé
        from .models import UserUsage

        usage = UserUsage(user_id=current_user_id)

    # Récupérer aussi les quotas pour calcul des pourcentages
    quotas = await quota_db.get_user_quotas(current_user_id)

    result = {
        "usage": usage.to_dict() if usage else {},
        "quotas": quotas.to_dict() if quotas else {},
        "percentages": {},
    }

    # Calculer les pourcentages d'usage
    if quotas:
        result["percentages"] = {
            "req_hour": (usage.req_hour / max(quotas.quota_req_hour or 1, 1)) * 100,
            "req_day": (usage.req_day / max(quotas.quota_req_day or 1, 1)) * 100,
            "cpu_seconds": (usage.cpu_seconds / max(quotas.quota_cpu_seconds or 1, 1))
            * 100,
            "mem_mb": (usage.mem_peak_mb / max(quotas.quota_mem_mb or 1, 1)) * 100,
            "storage_mb": (usage.storage_mb / max(quotas.quota_storage_mb or 1, 1))
            * 100,
            "files_count": (usage.files_count / max(quotas.quota_files_max or 1, 1))
            * 100,
        }

    return result


@user_router.get("/my/violations")
async def get_my_violations(
    current_user_id: str = Depends(get_current_user_id),
    hours: int = Query(24, description="Hours to look back"),
):
    """Récupère ses propres violations de quotas"""
    violations = await quota_db.get_quota_violations(current_user_id, hours)
    return {
        "violations": [v.to_dict() if hasattr(v, "to_dict") else v for v in violations],
        "total": len(violations),
        "hours": hours,
    }


# Endpoint pour les métriques Prometheus
@user_router.get("/metrics")
async def get_quota_metrics():
    """Endpoint pour les métriques Prometheus des quotas"""
    return get_quota_metrics_output()


# Fonctions utilitaires pour l'intégration
async def initialize_quota_system():
    """Initialise le système de quotas au démarrage de l'application"""
    try:
        # Tester la connexion à la base de données
        test_stats = await quota_db.get_usage_statistics()
        print(
            f"✅ Quota system initialized - tracking {test_stats['total_users']} users"
        )
        return True
    except Exception as e:
        print(f"❌ Failed to initialize quota system: {e}")
        return False


async def cleanup_quota_system():
    """Nettoie le système de quotas à l'arrêt de l'application"""
    try:
        # Nettoyer les anciennes violations
        await quota_db.cleanup_old_violations()
        print("✅ Quota system cleanup completed")
    except Exception as e:
        print(f"⚠️ Quota system cleanup warning: {e}")


# Tâches de maintenance à scheduler
async def hourly_maintenance():
    """Maintenance horaire du système de quotas"""
    try:
        await quota_db.reset_hourly_counters()
        print("✅ Hourly quota counters reset")
    except Exception as e:
        print(f"❌ Hourly maintenance failed: {e}")


async def daily_maintenance():
    """Maintenance quotidienne du système de quotas"""
    try:
        await quota_db.reset_daily_counters()
        await quota_db.cleanup_old_violations(30)  # Garder 30 jours
        print("✅ Daily quota maintenance completed")
    except Exception as e:
        print(f"❌ Daily maintenance failed: {e}")
