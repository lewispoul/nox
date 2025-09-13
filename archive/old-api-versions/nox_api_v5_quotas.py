"""
Enhanced Nox API with Quota System - Milestone 5
"""

import os
import pathlib
import shlex
import subprocess

# Import du middleware de sécurité Phase 2.1
import sys
import time
from typing import Optional

from fastapi import FastAPI, File, Header, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rate_limit_and_policy import RateLimitAndPolicyMiddleware

# Import des métriques Phase 2.2
sys.path.append(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "observability"
    )
)
from metrics_chatgpt import metrics_response, update_sandbox_metrics
from middleware import MetricsMiddleware

# Import du système de quotas Milestone 5
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quotas import (
    QuotaDatabase,
    QuotaEnforcementMiddleware,
    admin_router,
    get_quota_metrics_output,
    quota_metrics,
    user_router,
)

app = FastAPI(
    title="Nox API with Quotas",
    description="API sécurisée d'exécution de code - Milestone 5 avec Quotas Avancés",
    version="5.0.0",
)

# Configuration
NOX_METRICS_ENABLED = os.getenv("NOX_METRICS_ENABLED", "1") == "1"
NOX_QUOTAS_ENABLED = os.getenv("NOX_QUOTAS_ENABLED", "0") == "1"
NOX_TOKEN = os.getenv("NOX_API_TOKEN", "").strip()
SANDBOX = pathlib.Path(os.getenv("NOX_SANDBOX", "/home/nox/nox/sandbox")).resolve()
TIMEOUT_SEC = int(os.getenv("NOX_TIMEOUT", "20"))

SANDBOX.mkdir(parents=True, exist_ok=True)

# Initialisation du système de quotas
if NOX_QUOTAS_ENABLED:
    quota_db = QuotaDatabase()
    print(f"🚀 Quota system enabled - database: {quota_db.connection_string}")
else:
    quota_db = None
    print("ℹ️  Quota system disabled")

# Application des middlewares dans l'ordre
if NOX_QUOTAS_ENABLED and quota_db:
    app.add_middleware(QuotaEnforcementMiddleware, db=quota_db)
    print("✅ Quota enforcement middleware added")

app.add_middleware(MetricsMiddleware)
app.add_middleware(RateLimitAndPolicyMiddleware)

# Inclusion des routeurs de quotas
if NOX_QUOTAS_ENABLED:
    app.include_router(admin_router)
    app.include_router(user_router)
    print("✅ Quota admin and user routes added")


def check_auth(auth: str | None):
    if not NOX_TOKEN:
        return
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if auth.removeprefix("Bearer ").strip() != NOX_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


def safe_join(relpath: str) -> pathlib.Path:
    p = (SANDBOX / relpath.lstrip("/")).resolve()
    if SANDBOX not in p.parents and p != SANDBOX:
        raise HTTPException(status_code=400, detail="Path escapes sandbox")
    return p


# Helper pour extraire user_id depuis request (placeholder pour l'authentification)
def extract_user_id_from_request(request: Request) -> Optional[str]:
    """Extrait l'ID utilisateur de la requête - placeholder pour système auth"""
    # Pour les tests, utiliser un user_id fixe depuis les headers
    test_user_id = request.headers.get("x-test-user-id")
    if test_user_id:
        return test_user_id

    # Dans un vrai système, décoder le JWT ou utiliser la session
    # Pour l'instant, utiliser un ID par défaut pour les tests
    return "fc99e9b6-60d5-4856-af56-a5733e8c49b1"


@app.get("/health")
async def health(request: Request):
    """Endpoint de vérification de santé avec support quotas"""
    response = {"status": "ok", "sandbox": str(SANDBOX)}

    if NOX_QUOTAS_ENABLED:
        response["quota_system"] = "enabled"
        try:
            stats = await quota_db.get_usage_statistics()
            response["quota_stats"] = {
                "total_users": stats.get("total_users", 0),
                "violations_24h": stats.get("violations_last_24h", 0),
            }
        except Exception as e:
            response["quota_error"] = str(e)
    else:
        response["quota_system"] = "disabled"

    return response


# === ENDPOINT MÉTRIQUES PROMETHEUS COMBINÉES ===
@app.get("/metrics")
def metrics():
    if not NOX_METRICS_ENABLED:
        raise HTTPException(status_code=404, detail="metrics disabled")

    # Métriques existantes
    update_sandbox_metrics(os.getenv("NOX_SANDBOX", "/home/nox/nox/sandbox"))
    ct, payload = metrics_response()

    # Ajouter les métriques de quotas si activées
    if NOX_QUOTAS_ENABLED:
        quota_metrics_data = get_quota_metrics_output()
        payload += "\n" + quota_metrics_data

    return Response(content=payload, media_type=ct)


# === UPLOAD DE FICHIERS AVEC QUOTAS ===
@app.post("/put")
async def put(
    path: str,
    f: UploadFile = File(),
    request: Request = None,
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    check_auth(authorization)

    # Mettre l'user_id dans request.state pour le middleware de quotas
    if NOX_QUOTAS_ENABLED and request:
        user_id = extract_user_id_from_request(request)
        request.state.user_id = user_id

    data = f.file.read()
    target = safe_join(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)

    # Mettre à jour les métriques de stockage si quotas activés
    if NOX_QUOTAS_ENABLED and request and hasattr(request.state, "user_id"):
        try:
            # Calculer l'usage de stockage actuel
            total_size = sum(
                f.stat().st_size for f in SANDBOX.rglob("*") if f.is_file()
            )
            total_files = len(list(SANDBOX.rglob("*")))

            await quota_db.update_storage_usage(
                request.state.user_id,
                total_size // (1024 * 1024),  # Convert to MB
                total_files,
            )

            # Mettre à jour les métriques Prometheus
            quota_metrics.update_storage_usage(
                request.state.user_id, total_size // (1024 * 1024)
            )
            quota_metrics.update_files_count(request.state.user_id, total_files)
        except Exception as e:
            print(f"Warning: Could not update storage metrics: {e}")

    return {"message": f"Uploaded {len(data)} bytes to {path}"}


# === EXÉCUTION PYTHON AVEC QUOTAS ===
class RunPy(BaseModel):
    code: str
    filename: str = "run.py"


@app.post("/run_py")
async def run_py(
    body: RunPy,
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    check_auth(authorization)

    # Mettre l'user_id dans request.state pour le middleware de quotas
    if NOX_QUOTAS_ENABLED and request:
        user_id = extract_user_id_from_request(request)
        request.state.user_id = user_id

    target = safe_join(body.filename)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body.code)

    start_time = time.time()
    try:
        proc = subprocess.run(
            ["python3", str(target)],
            cwd=str(SANDBOX),
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SEC,
        )

        execution_time = time.time() - start_time

        # Mettre à jour les métriques CPU si quotas activés
        if NOX_QUOTAS_ENABLED and request and hasattr(request.state, "user_id"):
            try:
                await quota_db.add_cpu_usage(request.state.user_id, execution_time)
                quota_metrics.record_cpu_usage(request.state.user_id, execution_time)
            except Exception as e:
                print(f"Warning: Could not update CPU metrics: {e}")

        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Timeout")


# === EXÉCUTION SHELL AVEC QUOTAS ===
class RunSh(BaseModel):
    cmd: str


FORBIDDEN_COMMANDS = {
    "rm",
    "reboot",
    "shutdown",
    "mkfs",
    "dd",
    "mount",
    "umount",
    "sudo",
}


@app.post("/run_sh")
async def run_sh(
    body: RunSh,
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    check_auth(authorization)

    # Mettre l'user_id dans request.state pour le middleware de quotas
    if NOX_QUOTAS_ENABLED and request:
        user_id = extract_user_id_from_request(request)
        request.state.user_id = user_id

    try:
        cmd_parts = shlex.split(body.cmd)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid command syntax: {e}")

    if not cmd_parts:
        raise HTTPException(status_code=400, detail="Empty command")

    if cmd_parts[0] in FORBIDDEN_COMMANDS:
        raise HTTPException(
            status_code=400, detail=f"Forbidden command: {cmd_parts[0]}"
        )

    start_time = time.time()
    try:
        proc = subprocess.run(
            cmd_parts,
            cwd=str(SANDBOX),
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SEC,
        )

        execution_time = time.time() - start_time

        # Mettre à jour les métriques CPU si quotas activés
        if NOX_QUOTAS_ENABLED and request and hasattr(request.state, "user_id"):
            try:
                await quota_db.add_cpu_usage(request.state.user_id, execution_time)
                quota_metrics.record_cpu_usage(request.state.user_id, execution_time)
            except Exception as e:
                print(f"Warning: Could not update CPU metrics: {e}")

        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Timeout")


# === ENDPOINTS DE LISTING ===
@app.get("/ls")
async def ls(
    path: str = Query("", description="Chemin relatif dans le sandbox"),
    request: Request = None,
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    check_auth(authorization)

    # Mettre l'user_id dans request.state pour le middleware de quotas
    if NOX_QUOTAS_ENABLED and request:
        user_id = extract_user_id_from_request(request)
        request.state.user_id = user_id

    target = safe_join(path or ".")
    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    if target.is_file():
        return {"type": "file", "path": path, "size": target.stat().st_size}

    items = []
    for item in sorted(target.iterdir()):
        rel_path = str(item.relative_to(SANDBOX))
        if item.is_dir():
            items.append({"name": item.name, "type": "dir", "path": rel_path})
        else:
            items.append(
                {
                    "name": item.name,
                    "type": "file",
                    "path": rel_path,
                    "size": item.stat().st_size,
                }
            )

    return {"type": "dir", "path": path, "items": items}


# Event handlers pour initialisation et cleanup
@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage"""
    if NOX_QUOTAS_ENABLED:
        success = await initialize_quota_system()
        if success:
            print("✅ Nox API with Quota System ready!")
        else:
            print("⚠️  Nox API started but quota system has issues")
    else:
        print("✅ Nox API ready (quotas disabled)!")


@app.on_event("shutdown")
async def shutdown_event():
    """Nettoyage à l'arrêt"""
    if NOX_QUOTAS_ENABLED:
        from quotas.routes import cleanup_quota_system

        await cleanup_quota_system()
        print("👋 Quota system shutdown complete")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("NOX_PORT", "8081"))
    host = os.getenv("NOX_BIND_ADDR", "127.0.0.1")

    print(f"🚀 Starting Nox API v5.0.0 with Quotas on {host}:{port}")
    print(f"   Quotas: {'✅ ENABLED' if NOX_QUOTAS_ENABLED else '❌ DISABLED'}")
    print(f"   Metrics: {'✅ ENABLED' if NOX_METRICS_ENABLED else '❌ DISABLED'}")

    # Modes debug temporaire pour identifier les erreurs 500
    uvicorn.run(app, host=host, port=port, log_level="debug", reload=True)
