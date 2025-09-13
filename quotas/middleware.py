"""
Middleware for quota enforcement
"""

import os
import time
from typing import Any, Dict, Optional

import psutil
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .database import QuotaDatabase
from .metrics import quota_metrics
from .models import QuotaCheckResult, QuotaType


class QuotaEnforcementMiddleware(BaseHTTPMiddleware):
    """Middleware pour l'application des quotas utilisateur"""

    def __init__(self, app, db: QuotaDatabase):
        super().__init__(app)
        self.db = db
        self.enabled = os.getenv("NOX_QUOTAS_ENABLED", "0") == "1"
        self.quota_cache: Dict[str, tuple[Dict[str, Any], float]] = (
            {}
        )  # Cache des quotas avec timestamp
        self.cache_ttl = 60  # TTL du cache en secondes

    async def dispatch(self, request: Request, call_next):
        """Traite chaque requête avec vérification des quotas"""
        start_time = time.time()

        # Bypass si les quotas ne sont pas activés
        if not self.enabled:
            response = await call_next(request)
            return response

        # Extraire l'ID utilisateur depuis la requête (depuis JWT ou auth)
        user_id = await self._extract_user_id(request)
        if not user_id:
            # Pas d'utilisateur identifié, passer la requête
            response = await call_next(request)
            return response

        # Vérifier les quotas avant traitement
        quota_check = await self._check_quotas_before_request(user_id, request)
        if not quota_check.allowed:
            # Quota dépassé - bloquer la requête
            await self._record_quota_violation(user_id, quota_check)
            return self._create_quota_exceeded_response(quota_check)

        # Traitement de la requête avec surveillance
        response = await self._process_request_with_monitoring(
            request, call_next, user_id, start_time
        )

        return response

    async def _extract_user_id(self, request: Request) -> Optional[str]:
        """Extrait l'ID utilisateur de la requête"""
        # Essayer depuis les attributs de la requête (mis par le middleware d'auth)
        if hasattr(request.state, "user_id"):
            return request.state.user_id

        # Essayer depuis le header Authorization Bearer token
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "").strip()
            if token:
                # Pour ce test, nous cherchons un utilisateur avec oauth_id = token
                # Cela permet d'associer les tokens API aux utilisateurs de la base
                user = await self.db.get_user_by_oauth_id(token)
                if user:
                    return str(user["id"])

        # Essayer depuis le header Authorization JWT (si décodé)
        if hasattr(request.state, "user"):
            user = request.state.user
            if hasattr(user, "id"):
                return user.id
            elif isinstance(user, dict) and "id" in user:
                return user["id"]

        return None

    async def _check_quotas_before_request(
        self, user_id: str, request: Request
    ) -> QuotaCheckResult:
        """Vérifie les quotas avant de traiter la requête"""

        # Vérifier le quota de requêtes par heure
        hourly_check = await self._check_hourly_requests(user_id)
        if not hourly_check.allowed:
            return hourly_check

        # Vérifier le quota de requêtes par jour
        daily_check = await self._check_daily_requests(user_id)
        if not daily_check.allowed:
            return daily_check

        # Pour les endpoints qui consomment des ressources, vérifier les autres quotas
        if self._is_resource_intensive_endpoint(request.url.path):
            # Vérifier le stockage
            storage_check = await self._check_storage_quota(user_id)
            if not storage_check.allowed:
                return storage_check

            # Vérifier le nombre de fichiers
            files_check = await self._check_files_quota(user_id)
            if not files_check.allowed:
                return files_check

        # Tous les quotas OK
        return QuotaCheckResult(
            allowed=True,
            quota_type=QuotaType.REQUESTS_HOUR,
            current_usage=0,
            limit=0,
            percentage=0.0,
            message="All quotas OK",
        )

    async def _check_hourly_requests(self, user_id: str) -> QuotaCheckResult:
        """Vérifie le quota de requêtes par heure"""
        quotas = await self._get_user_quotas(user_id)
        usage = await self.db.get_user_usage(user_id)

        limit = quotas.get("quota_req_hour", 100)
        current = usage.req_hour if usage else 0

        return QuotaCheckResult(
            allowed=current < limit,
            quota_type=QuotaType.REQUESTS_HOUR,
            current_usage=current,
            limit=limit,
            percentage=current / max(limit, 1),
            message=f"Hourly requests: {current}/{limit}",
        )

    async def _check_daily_requests(self, user_id: str) -> QuotaCheckResult:
        """Vérifie le quota de requêtes par jour"""
        quotas = await self._get_user_quotas(user_id)
        usage = await self.db.get_user_usage(user_id)

        limit = quotas.get("quota_req_day", 1000)
        current = usage.req_day if usage else 0

        return QuotaCheckResult(
            allowed=current < limit,
            quota_type=QuotaType.REQUESTS_DAY,
            current_usage=current,
            limit=limit,
            percentage=current / max(limit, 1),
            message=f"Daily requests: {current}/{limit}",
        )

    async def _check_storage_quota(self, user_id: str) -> QuotaCheckResult:
        """Vérifie le quota de stockage"""
        quotas = await self._get_user_quotas(user_id)
        usage = await self.db.get_user_usage(user_id)

        limit = quotas.get("quota_storage_mb", 100)
        current = usage.storage_mb if usage else 0

        return QuotaCheckResult(
            allowed=current < limit,
            quota_type=QuotaType.STORAGE_MB,
            current_usage=current,
            limit=limit,
            percentage=current / max(limit, 1),
            message=f"Storage usage: {current}/{limit} MB",
        )

    async def _check_files_quota(self, user_id: str) -> QuotaCheckResult:
        """Vérifie le quota de nombre de fichiers"""
        quotas = await self._get_user_quotas(user_id)
        usage = await self.db.get_user_usage(user_id)

        limit = quotas.get("quota_files_max", 50)
        current = usage.files_count if usage else 0

        return QuotaCheckResult(
            allowed=current < limit,
            quota_type=QuotaType.FILES_MAX,
            current_usage=current,
            limit=limit,
            percentage=current / max(limit, 1),
            message=f"Files count: {current}/{limit}",
        )

    def _is_resource_intensive_endpoint(self, path: str) -> bool:
        """Détermine si un endpoint consomme des ressources"""
        resource_endpoints = ["/run_py", "/run_sh", "/put"]
        return any(endpoint in path for endpoint in resource_endpoints)

    async def _get_user_quotas(self, user_id: str) -> Dict[str, Any]:
        """Récupère les quotas utilisateur avec cache"""
        cache_key = f"quotas_{user_id}"
        now = time.time()

        # Vérifier le cache
        if cache_key in self.quota_cache:
            cached_data, timestamp = self.quota_cache[cache_key]
            if now - timestamp < self.cache_ttl:
                return cached_data

        # Récupérer depuis la DB
        quotas = await self.db.get_user_quotas(user_id)
        if quotas:
            quotas_dict = quotas.to_dict()
            self.quota_cache[cache_key] = (quotas_dict, now)
            return quotas_dict

        # Quotas par défaut
        default_quotas = {
            "quota_req_hour": 100,
            "quota_req_day": 1000,
            "quota_cpu_seconds": 300,
            "quota_mem_mb": 512,
            "quota_storage_mb": 100,
            "quota_files_max": 50,
        }
        self.quota_cache[cache_key] = (default_quotas, now)
        return default_quotas

    async def _process_request_with_monitoring(
        self, request: Request, call_next, user_id: str, start_time: float
    ) -> Response:
        """Traite la requête avec surveillance des ressources"""

        # Surveiller le processus actuel pour la mémoire
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        initial_cpu_time = process.cpu_times().user + process.cpu_times().system

        try:
            # Traiter la requête
            response = await call_next(request)

            # Mesurer les ressources après traitement
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            final_cpu_time = process.cpu_times().user + process.cpu_times().system

            # Calculer la consommation
            memory_used = max(0, final_memory - initial_memory)
            cpu_used = max(0, final_cpu_time - initial_cpu_time)
            duration = time.time() - start_time

            # Mettre à jour les métriques et usage
            await self._update_usage_after_request(
                user_id, request, response, duration, cpu_used, memory_used
            )

            return response

        except Exception as e:
            # Même en cas d'erreur, enregistrer la requête
            duration = time.time() - start_time
            await self._record_failed_request(user_id, request, duration, str(e))
            raise

    async def _update_usage_after_request(
        self,
        user_id: str,
        request: Request,
        response: Response,
        duration: float,
        cpu_seconds: float,
        memory_mb: float,
    ):
        """Met à jour l'usage après traitement de la requête"""

        # Incrémenter les compteurs de requêtes
        await self.db.increment_request_counters(user_id)

        # Enregistrer la consommation CPU si significative
        if cpu_seconds > 0.001:  # Plus de 1ms
            await self.db.add_cpu_usage(user_id, cpu_seconds)

        # Mettre à jour le pic mémoire si nécessaire
        if memory_mb > 10:  # Plus de 10MB
            await self.db.update_memory_peak(user_id, int(memory_mb))

        # Enregistrer les métriques Prometheus
        quota_metrics.record_request(
            user_id=user_id,
            endpoint=request.url.path,
            status_code=response.status_code,
            duration=duration,
        )

        if cpu_seconds > 0.001:
            quota_metrics.record_cpu_usage(user_id, cpu_seconds)

        if memory_mb > 10:
            quota_metrics.update_memory_peak(user_id, int(memory_mb))

    async def _record_quota_violation(
        self, user_id: str, quota_check: QuotaCheckResult
    ):
        """Enregistre une violation de quota"""
        await self.db.record_quota_violation(
            user_id=user_id,
            reason=quota_check.quota_type.value,
            detail={
                "current_usage": quota_check.current_usage,
                "limit": quota_check.limit,
                "percentage": quota_check.percentage,
                "message": quota_check.message,
            },
        )

        quota_metrics.record_quota_violation(user_id, quota_check.quota_type.value)

    async def _record_failed_request(
        self, user_id: str, request: Request, duration: float, error: str
    ):
        """Enregistre une requête qui a échoué"""
        quota_metrics.record_request(
            user_id=user_id,
            endpoint=request.url.path,
            status_code=500,
            duration=duration,
        )

        # Incrémenter quand même le compteur de requêtes
        await self.db.increment_request_counters(user_id)

    def _create_quota_exceeded_response(
        self, quota_check: QuotaCheckResult
    ) -> JSONResponse:
        """Crée une réponse d'erreur pour quota dépassé"""
        status_code = (
            429
            if quota_check.quota_type
            in [QuotaType.REQUESTS_HOUR, QuotaType.REQUESTS_DAY]
            else 403
        )

        return JSONResponse(
            status_code=status_code,
            content={
                "error": "Quota exceeded",
                "quota_type": quota_check.quota_type.value,
                "current_usage": quota_check.current_usage,
                "limit": quota_check.limit,
                "percentage": round(quota_check.percentage * 100, 1),
                "message": quota_check.message,
                "retry_after": self._calculate_retry_after(quota_check.quota_type),
            },
        )

    def _calculate_retry_after(self, quota_type: QuotaType) -> int:
        """Calcule le délai Retry-After en secondes"""
        if quota_type == QuotaType.REQUESTS_HOUR:
            return 3600  # 1 heure
        elif quota_type == QuotaType.REQUESTS_DAY:
            return 86400  # 24 heures
        else:
            return 3600  # Par défaut 1 heure
