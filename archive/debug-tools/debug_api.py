#!/usr/bin/env python3
"""
Version debug de l'API Nox v5 pour identifier les erreurs 500
Désactive temporairement les middlewares de sécurité
"""
import os
import traceback

from fastapi import FastAPI
from fastapi.responses import JSONResponse

# Variables globales pour l'état du système de quotas
NOX_QUOTAS_ENABLED = os.getenv("NOX_QUOTAS_ENABLED", "0") == "1"

# Imports des modules quotas
if NOX_QUOTAS_ENABLED:
    from quotas.database import QuotaDatabase
    from quotas.routes import admin_router, user_router

    # Initialisation de la base de données des quotas
    quota_db = QuotaDatabase()
else:
    quota_db = None

app = FastAPI(
    title="Nox API Debug",
    description="Version debug pour identifier les erreurs 500",
    version="5.0.0-debug",
)


# Middleware d'erreur global pour capturer les stack traces
@app.middleware("http")
async def debug_errors(request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        print(f"❌ ERROR in {request.method} {request.url.path}")
        print(f"Exception: {type(e).__name__}: {e}")
        print("Stack trace:")
        traceback.print_exc()

        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "debug": str(e),
                "type": type(e).__name__,
            },
        )


# Simulation d'extraction d'utilisateur simple
def extract_user_id_from_token(token: str) -> str:
    """Extraction simple de l'utilisateur depuis le token"""
    if token == "test123":
        # Retourner l'UUID de notre utilisateur test
        return "81dfa919-4604-4fdf-8038-4b862ee2a469"
    return token


@app.get("/health")
async def health():
    """Test simple de santé"""
    return {"status": "ok", "quotas": "enabled" if NOX_QUOTAS_ENABLED else "disabled"}


@app.get("/debug/quotas/test")
async def debug_quotas():
    """Test de connexion à la base des quotas"""
    if not quota_db:
        return {"error": "Quota DB not initialized"}

    try:
        # Test de connexion
        conn = await quota_db.connect()
        await conn.close()
        return {"status": "quota_db_connection_ok"}
    except Exception as e:
        return {"error": f"Quota DB connection failed: {e}"}


@app.get("/debug/user/test123")
async def debug_user_test123():
    """Test de récupération de l'utilisateur test123"""
    if not quota_db:
        return {"error": "Quota DB not initialized"}

    try:
        # Test get_user_by_oauth_id
        user = await quota_db.get_user_by_oauth_id("test123")
        if user:
            return {"status": "user_found", "user": user}
        else:
            return {"error": "User test123 not found"}
    except Exception as e:
        return {"error": f"Error getting user: {e}"}


@app.get("/debug/quotas/user/{user_id}")
async def debug_user_quotas(user_id: str):
    """Test de récupération des quotas utilisateur"""
    if not quota_db:
        return {"error": "Quota DB not initialized"}

    try:
        quotas = await quota_db.get_user_quotas(user_id)
        if quotas:
            return {"status": "quotas_found", "quotas": quotas.to_dict()}
        else:
            return {"error": f"No quotas found for user {user_id}"}
    except Exception as e:
        return {"error": f"Error getting quotas: {e}", "user_id": user_id}


# Ajouter les routes de quotas si activées
if NOX_QUOTAS_ENABLED and quota_db:
    print("📊 Adding quota routes for debug...")
    app.include_router(admin_router)
    app.include_router(user_router)

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("NOX_PORT", "8083"))

    print(f"🔍 Starting Nox API Debug on 127.0.0.1:{port}")
    print(f"   Quotas: {'✅ ENABLED' if NOX_QUOTAS_ENABLED else '❌ DISABLED'}")

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="debug")
