"""
Enhanced Nox API v6.0.0 with Advanced Audit System - M6 Implementation
Date: August 13, 2025

Features:
- Comprehensive audit logging with session tracking
- Admin interface for audit management
- CSV/JSON export capabilities
- Prometheus audit metrics integration
- Enhanced user/action tracking
"""

import os
import pathlib
import subprocess

# Import existing middleware components
import sys
import tempfile
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from admin_audit_api import admin_router

# Import M6 audit components
from advanced_audit_middleware import (
    AdvancedAuditMiddleware,
    get_audit_metrics,
    initialize_audit_system,
    shutdown_audit_system,
)
from rate_limit_and_policy import RateLimitAndPolicyMiddleware

# Import existing metrics
sys.path.append(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "observability"
    )
)
from metrics_chatgpt import metrics_response, update_sandbox_metrics
from middleware import MetricsMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle with audit system"""
    # Startup
    database_url = os.getenv(
        "DATABASE_URL", "postgresql://noxuser:test_password_123@localhost:5432/noxdb"
    )
    await initialize_audit_system(database_url)
    print("🔍 M6 Advanced Audit System initialized")

    yield

    # Shutdown
    await shutdown_audit_system()
    print("🔍 Audit system shutdown complete")


app = FastAPI(
    title="Nox API",
    description="API sécurisée d'exécution de code - Phase 2 M6 avec Audit Avancé",
    version="6.0.0",
    lifespan=lifespan,
)

NOX_METRICS_ENABLED = os.getenv("NOX_METRICS_ENABLED", "1") == "1"
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://noxuser:test_password_123@localhost:5432/noxdb"
)

# Application des middlewares dans l'ordre recommandé
# 1. Metrics first (outer layer)
app.add_middleware(MetricsMiddleware)

# 2. Advanced Audit (M6 - new comprehensive audit)
app.add_middleware(AdvancedAuditMiddleware, database_url=DATABASE_URL)

# 3. Rate limiting and policy (inner layer, closest to endpoints)
app.add_middleware(RateLimitAndPolicyMiddleware)

# Include admin audit router
app.include_router(admin_router)

NOX_TOKEN = os.getenv("NOX_API_TOKEN", "").strip()
SANDBOX = pathlib.Path(os.getenv("NOX_SANDBOX", "/home/nox/nox/sandbox")).resolve()
TIMEOUT_SEC = int(os.getenv("NOX_TIMEOUT", "20"))

SANDBOX.mkdir(parents=True, exist_ok=True)


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


@app.get("/health")
async def health(request: Request):
    """Endpoint de vérification de santé avec audit intégré"""
    if NOX_METRICS_ENABLED:
        update_sandbox_metrics(str(SANDBOX))

    return {
        "status": "healthy",
        "version": "6.0.0",
        "features": ["audit_logging", "admin_interface", "export_capabilities"],
        "audit": "enabled",
        "timestamp": time.time(),
    }


@app.get("/metrics")
async def metrics(request: Request):
    """Métriques Prometheus combinées avec métriques d'audit"""
    base_metrics = metrics_response()[1].decode("utf-8")
    audit_metrics = get_audit_metrics()

    # Combine both metrics
    combined_metrics = base_metrics + "\n# M6 Audit Metrics\n" + audit_metrics

    return Response(content=combined_metrics, media_type="text/plain")


# === GESTION DE FICHIERS ===


@app.get("/ls")
def ls(
    path: str = ".",
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    """Liste les fichiers et dossiers avec audit détaillé"""
    check_auth(authorization)

    target = safe_join(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    if target.is_file():
        stat = target.stat()
        return {
            "type": "file",
            "path": path,
            "size": stat.st_size,
            "modified": stat.st_mtime,
        }

    files = []
    for item in target.iterdir():
        try:
            stat = item.stat()
            files.append(
                {
                    "name": item.name + ("/" if item.is_dir() else ""),
                    "size": stat.st_size if item.is_file() else None,
                    "modified": stat.st_mtime,
                }
            )
        except (OSError, ValueError):
            continue

    return {"type": "directory", "path": path, "files": files}


@app.get("/cat")
def cat(
    path: str, authorization: str | None = Header(default=None, alias="Authorization")
):
    """Lecture de fichiers avec audit de contenu"""
    check_auth(authorization)

    target = safe_join(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    if not target.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    try:
        content = target.read_text(encoding="utf-8")
        return {"content": content, "file_path": path, "size": len(content)}
    except UnicodeDecodeError:
        content_bytes = target.read_bytes()
        return {
            "content": f"<binary file, {len(content_bytes)} bytes>",
            "file_path": path,
        }


@app.put("/write")
async def write_file(
    path: str,
    file: UploadFile = File(...),
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    """Écriture de fichiers avec audit détaillé"""
    check_auth(authorization)

    target = safe_join(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    content = await file.read()
    target.write_bytes(content)

    # The audit middleware will automatically log this with file details
    return {
        "message": f"File written to {path}",
        "size": len(content),
        "file_path": path,
    }


@app.delete("/delete")
def delete(
    path: str, authorization: str | None = Header(default=None, alias="Authorization")
):
    """Suppression de fichiers avec audit de sécurité"""
    check_auth(authorization)

    target = safe_join(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    original_size = 0
    files_count = 0

    if target.is_file():
        original_size = target.stat().st_size
        files_count = 1
        target.unlink()
        message = f"Deleted file {path}"
    elif target.is_dir():
        import shutil

        # Calculate directory size before deletion
        for root, dirs, files in os.walk(target):
            files_count += len(files)
            for file in files:
                try:
                    original_size += os.path.getsize(os.path.join(root, file))
                except:
                    pass
        shutil.rmtree(target)
        message = f"Deleted directory {path}"

    return {
        "message": message,
        "files_deleted": files_count,
        "bytes_freed": original_size,
    }


# === EXÉCUTION DE CODE ===


class ExecuteRequest(BaseModel):
    command: str = Field(..., max_length=10000, description="Command to execute")
    timeout: Optional[int] = Field(
        default=None, ge=1, le=300, description="Timeout in seconds"
    )


@app.post("/run")
def run_command(
    request: ExecuteRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    """Exécution de commandes avec audit complet"""
    check_auth(authorization)

    timeout = request.timeout or TIMEOUT_SEC
    start_time = time.time()

    # Déterminer le type de commande
    command_type = "bash"  # default
    if request.command.strip().startswith("python"):
        command_type = "python"
    elif request.command.strip().startswith("node"):
        command_type = "nodejs"
    elif request.command.strip().startswith(
        "npm"
    ) or request.command.strip().startswith("npx"):
        command_type = "nodejs"

    try:
        with tempfile.TemporaryDirectory(dir=SANDBOX) as tmpdir:
            result = subprocess.run(
                ["bash", "-c", request.command],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, "HOME": tmpdir, "TMPDIR": tmpdir},
            )

            execution_time = int((time.time() - start_time) * 1000)

            response = {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "execution_time_ms": execution_time,
                "command_type": command_type,
                "timeout_used": timeout,
                "success": result.returncode == 0,
            }

            if NOX_METRICS_ENABLED:
                update_sandbox_metrics(str(SANDBOX))

            return response

    except subprocess.TimeoutExpired:
        execution_time = int((time.time() - start_time) * 1000)
        raise HTTPException(
            status_code=408,
            detail={
                "error": "Command timed out",
                "timeout": timeout,
                "execution_time_ms": execution_time,
                "command_type": command_type,
            },
        )
    except Exception as e:
        execution_time = int((time.time() - start_time) * 1000)
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "execution_time_ms": execution_time,
                "command_type": command_type,
            },
        )


# === ENDPOINTS D'ADMINISTRATION M6 ===


@app.get("/admin/audit/status")
async def audit_status(
    authorization: str | None = Header(default=None, alias="Authorization")
):
    """Statut du système d'audit - endpoint admin"""
    # Simple admin check - you should implement proper admin auth
    if not authorization or "admin" not in authorization.lower():
        raise HTTPException(status_code=403, detail="Admin access required")

    from advanced_audit_middleware import db_connection

    db_status = "connected" if db_connection.pool else "disconnected"

    return {
        "audit_system": "active",
        "version": "6.0.0",
        "database_status": db_status,
        "features": {
            "session_tracking": True,
            "detailed_logging": True,
            "metrics_integration": True,
            "admin_interface": True,
            "export_capabilities": True,
        },
    }


@app.get("/admin/stats")
async def admin_stats(
    authorization: str | None = Header(default=None, alias="Authorization")
):
    """Statistiques administratives rapides"""
    if not authorization or "admin" not in authorization.lower():
        raise HTTPException(status_code=403, detail="Admin access required")

    from advanced_audit_middleware import db_connection

    if not db_connection.pool:
        raise HTTPException(status_code=500, detail="Database not available")

    try:
        async with db_connection.pool.acquire() as conn:
            # Get quick stats
            stats = {}

            # Total actions today
            stats["actions_today"] = await conn.fetchval(
                "SELECT COUNT(*) FROM audit_actions WHERE timestamp >= CURRENT_DATE"
            )

            # Unique users today
            stats["users_today"] = await conn.fetchval(
                "SELECT COUNT(DISTINCT user_id) FROM audit_actions WHERE timestamp >= CURRENT_DATE"
            )

            # Active sessions
            stats["active_sessions"] = await conn.fetchval(
                "SELECT COUNT(*) FROM audit_sessions WHERE is_active = true"
            )

            # Error rate today
            total_today = stats["actions_today"]
            errors_today = await conn.fetchval(
                "SELECT COUNT(*) FROM audit_actions WHERE timestamp >= CURRENT_DATE AND success = false"
            )
            stats["error_rate_today"] = (errors_today / max(total_today, 1)) * 100

            return stats

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats error: {str(e)}")


# === LANCEMENT DU SERVEUR ===
if __name__ == "__main__":
    import uvicorn

    host = os.getenv("NOX_BIND_ADDR", "127.0.0.1")
    port = int(os.getenv("NOX_PORT", "8082"))

    print("🚀 Starting Nox API v6.0.0 with M6 Advanced Audit")
    print(f"   - Database: {DATABASE_URL}")
    print("   - Audit: Enabled with session tracking")
    print("   - Admin: /admin/audit/* endpoints available")
    print("   - Export: CSV/JSON capabilities enabled")

    uvicorn.run(app, host=host, port=port)
