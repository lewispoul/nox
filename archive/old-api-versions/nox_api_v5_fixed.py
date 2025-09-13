#!/usr/bin/env python3
"""
Nox API v5 with Quotas - Production Ready Version
Based on debug fixes from Milestone 5.3
"""
import os
import pathlib
import subprocess
import tempfile
import time

from fastapi import FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import Response

# Import des métriques Phase 2.2
from metrics_chatgpt import metrics_response, update_sandbox_metrics
from middleware import MetricsMiddleware

# Import du middleware de sécurité Phase 2.1
from rate_limit_and_policy import RateLimitAndPolicyMiddleware

# Import du système de quotas Milestone 5
from quotas.database import QuotaDatabase
from quotas.metrics import get_quota_metrics_output, quota_metrics
from quotas.middleware import QuotaEnforcementMiddleware
from quotas.routes import admin_router, user_router

# Configuration globale
NOX_QUOTAS_ENABLED = os.getenv("NOX_QUOTAS_ENABLED", "0") == "1"
NOX_METRICS_ENABLED = os.getenv("NOX_METRICS_ENABLED", "1") == "1"
NOX_TOKEN = os.getenv("NOX_API_TOKEN", "").strip()
SANDBOX = pathlib.Path(os.getenv("NOX_SANDBOX", "/home/nox/nox/sandbox")).resolve()
TIMEOUT_SEC = int(os.getenv("NOX_TIMEOUT", "20"))

SANDBOX.mkdir(parents=True, exist_ok=True)

# Initialisation de la base de données des quotas
quota_db = QuotaDatabase() if NOX_QUOTAS_ENABLED else None

app = FastAPI(
    title="Nox API with Quotas",
    description="API sécurisée d'exécution de code avec système de quotas avancé",
    version="5.0.0",
)

# Application des middlewares dans l'ordre
if NOX_METRICS_ENABLED:
    app.add_middleware(MetricsMiddleware)

# Middleware de quotas AVANT le middleware de sécurité pour intercepter tôt
if NOX_QUOTAS_ENABLED and quota_db:
    print("✅ Quota enforcement middleware added")
    app.add_middleware(QuotaEnforcementMiddleware, db=quota_db)

app.add_middleware(RateLimitAndPolicyMiddleware)


def check_auth(auth: str | None):
    """Vérification de l'authentification"""
    if not NOX_TOKEN:
        return
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if auth.removeprefix("Bearer ").strip() != NOX_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


def safe_join(relpath: str) -> pathlib.Path:
    """Création de chemin sécurisé dans le sandbox"""
    p = (SANDBOX / relpath.lstrip("/")).resolve()
    if SANDBOX not in p.parents and p != SANDBOX:
        raise HTTPException(status_code=400, detail="Path escapes sandbox")
    return p


# === ENDPOINTS PRINCIPAUX ===


@app.get("/health")
async def health(request: Request):
    """Endpoint de vérification de santé avec stats de quotas"""
    response = {"status": "ok", "sandbox": str(SANDBOX)}

    # Ajouter les stats de quotas si activées
    if NOX_QUOTAS_ENABLED and quota_db:
        try:
            stats = await quota_db.get_usage_statistics()
            response["quota_system"] = "enabled"
            response["quota_stats"] = {
                "total_users": stats.get("total_users", 0),
                "violations_24h": stats.get("violations_24h", 0),
            }
        except Exception as e:
            response["quota_system"] = f"error: {e}"
    else:
        response["quota_system"] = "disabled"

    return response


@app.get("/ls")
async def list_files(
    request: Request, path: str = "", authorization: str | None = Header(None)
):
    """Liste les fichiers dans le sandbox"""
    check_auth(authorization)

    try:
        target_path = safe_join(path)
        if not target_path.exists():
            raise HTTPException(status_code=404, detail="Path not found")

        if target_path.is_file():
            return {"type": "file", "path": str(target_path.relative_to(SANDBOX))}

        # Listing directory
        files = []
        for item in target_path.iterdir():
            relative_path = str(item.relative_to(SANDBOX))
            files.append(
                {
                    "name": item.name,
                    "path": relative_path,
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None,
                }
            )

        # Calcul des statistiques pour les quotas
        if NOX_QUOTAS_ENABLED and quota_db and hasattr(request.state, "user_id"):
            total_files = len([f for f in files if f["type"] == "file"])
            total_size = sum(
                f["size"] for f in files if f["type"] == "file" and f["size"]
            )

            # Mise à jour usage storage et files
            try:
                await quota_db.update_storage_usage(
                    request.state.user_id,
                    total_size // (1024 * 1024),  # Convertir en MB
                    total_files,
                )

                # Métriques Prometheus
                quota_metrics.update_storage_usage(
                    request.state.user_id, total_size // (1024 * 1024)
                )
                quota_metrics.update_files_count(request.state.user_id, total_files)
            except Exception as e:
                print(f"Warning: Could not update quota usage: {e}")

        return {"type": "directory", "files": files, "total": len(files)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing files: {e}")


@app.post("/put")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    path: str = "/",
    authorization: str | None = Header(None),
):
    """Upload un fichier dans le sandbox"""
    check_auth(authorization)

    try:
        target_path = safe_join(path) / file.filename
        target_path.parent.mkdir(parents=True, exist_ok=True)

        content = await file.read()
        with open(target_path, "wb") as f:
            f.write(content)

        # Mise à jour des métriques de quota si activées
        if NOX_QUOTAS_ENABLED and quota_db and hasattr(request.state, "user_id"):
            try:
                size_mb = len(content) // (1024 * 1024)
                await quota_db.update_storage_usage(
                    request.state.user_id, size_mb, 1
                )  # 1 fichier uploadé
                quota_metrics.update_storage_usage(request.state.user_id, size_mb)
            except Exception as e:
                print(f"Warning: Could not update quota usage: {e}")

        return {
            "message": "File uploaded successfully",
            "path": str(target_path.relative_to(SANDBOX)),
            "size": len(content),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {e}")


@app.post("/run_py")
async def run_python(
    request: Request, code: dict, authorization: str | None = Header(None)
):
    """Exécute du code Python dans le sandbox"""
    check_auth(authorization)

    if "code" not in code:
        raise HTTPException(status_code=400, detail="'code' field required")

    try:
        # Créer fichier temporaire
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, dir=SANDBOX
        ) as f:
            f.write(code["code"])
            temp_file = pathlib.Path(f.name)

        start_time = time.time()

        # Exécution
        result = subprocess.run(
            ["python3", str(temp_file)],
            cwd=SANDBOX,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SEC,
        )

        execution_time = time.time() - start_time

        # Mise à jour des métriques CPU si quotas activés
        if NOX_QUOTAS_ENABLED and quota_db and hasattr(request.state, "user_id"):
            try:
                await quota_db.add_cpu_usage(request.state.user_id, execution_time)
                quota_metrics.record_cpu_usage(request.state.user_id, execution_time)
            except Exception as e:
                print(f"Warning: Could not update quota usage: {e}")

        # Nettoyage
        temp_file.unlink(missing_ok=True)

        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "execution_time": round(execution_time, 3),
        }

    except subprocess.TimeoutExpired:
        temp_file.unlink(missing_ok=True)
        raise HTTPException(status_code=408, detail="Execution timeout")
    except Exception as e:
        if "temp_file" in locals():
            temp_file.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Execution error: {e}")


@app.post("/run_sh")
async def run_shell(
    request: Request, cmd: dict, authorization: str | None = Header(None)
):
    """Exécute une commande shell dans le sandbox"""
    check_auth(authorization)

    if "cmd" not in cmd:
        raise HTTPException(status_code=400, detail="'cmd' field required")

    try:
        start_time = time.time()

        # Exécution sécurisée
        result = subprocess.run(
            cmd["cmd"],
            shell=True,
            cwd=SANDBOX,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SEC,
        )

        execution_time = time.time() - start_time

        # Mise à jour des métriques CPU si quotas activés
        if NOX_QUOTAS_ENABLED and quota_db and hasattr(request.state, "user_id"):
            try:
                await quota_db.add_cpu_usage(request.state.user_id, execution_time)
                quota_metrics.record_cpu_usage(request.state.user_id, execution_time)
            except Exception as e:
                print(f"Warning: Could not update quota usage: {e}")

        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "execution_time": round(execution_time, 3),
        }

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Execution timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution error: {e}")


# === ENDPOINT MÉTRIQUES PROMETHEUS COMBINÉES ===
@app.get("/metrics")
def metrics():
    """Endpoint Prometheus avec métriques système + quotas"""
    if not NOX_METRICS_ENABLED:
        raise HTTPException(status_code=404, detail="Metrics disabled")

    try:
        # Métriques existantes
        update_sandbox_metrics(str(SANDBOX))
        ct, payload = metrics_response()

        # Convertir les bytes en string pour la concaténation
        payload_str = (
            payload.decode("utf-8") if isinstance(payload, bytes) else str(payload)
        )

        # Ajouter les métriques de quotas si activées
        if NOX_QUOTAS_ENABLED:
            quota_metrics_data = get_quota_metrics_output()
            payload_str += "\n" + quota_metrics_data

        return Response(content=payload_str, media_type=ct)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating metrics: {e}")


# === AJOUT DES ROUTES DE QUOTAS ===
if NOX_QUOTAS_ENABLED and quota_db:
    print("✅ Quota admin and user routes added")
    app.include_router(admin_router)
    app.include_router(user_router)


# === ÉVÉNEMENTS DE CYCLE DE VIE ===
@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage"""
    if NOX_QUOTAS_ENABLED and quota_db:
        try:
            # Test de connexion
            conn = await quota_db.connect()
            await conn.close()

            # Statistiques initiales
            stats = await quota_db.get_usage_statistics()
            print(
                f"✅ Quota system initialized - tracking {stats.get('total_users', 0)} users"
            )
        except Exception as e:
            print(f"⚠️ Warning: Quota system startup error: {e}")

    print("✅ Nox API with Quota System ready!")


@app.on_event("shutdown")
async def shutdown_event():
    """Nettoyage à l'arrêt"""
    print("👋 Quota system shutdown complete")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("NOX_PORT", "8081"))
    host = os.getenv("NOX_BIND_ADDR", "127.0.0.1")

    print(f"🚀 Starting Nox API v5.0.0 with Quotas on {host}:{port}")
    print(f"   Quotas: {'✅ ENABLED' if NOX_QUOTAS_ENABLED else '❌ DISABLED'}")
    print(f"   Metrics: {'✅ ENABLED' if NOX_METRICS_ENABLED else '❌ DISABLED'}")

    uvicorn.run(app, host=host, port=port, log_level="info")
