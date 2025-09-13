import os
import pathlib
import shlex
import subprocess
import sys

# Solution rapide ChatGPT pour les imports
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

# ROOT = nox-api-src/
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# Import du module d'authentification
from auth import User, UserRole, auth_router, db, get_current_user, optional_auth
from observability.metrics_chatgpt import metrics_response, update_sandbox_metrics
from observability.middleware import MetricsMiddleware

app = FastAPI(
    title="Nox API",
    description="API sécurisée d'exécution de code - Phase 2.3 avec Authentification RBAC",
    version="2.3.0",
)

NOX_METRICS_ENABLED = os.getenv("NOX_METRICS_ENABLED", "1") == "1"

# Application des middlewares - temporairement sans sécurité pour test
app.add_middleware(MetricsMiddleware)
# app.add_middleware(RateLimitAndPolicyMiddleware)  # Désactivé temporairement

# Inclure les routes d'authentification
app.include_router(auth_router)

NOX_TOKEN = os.getenv("NOX_API_TOKEN", "").strip()
SANDBOX = pathlib.Path(os.getenv("NOX_SANDBOX", "/home/nox/nox/sandbox")).resolve()
TIMEOUT_SEC = int(os.getenv("NOX_TIMEOUT", "20"))

SANDBOX.mkdir(parents=True, exist_ok=True)


def check_auth_legacy(auth: str | None):
    """Vérification de l'ancien système d'authentification (fallback)"""
    # Désactivé temporairement pour test - gardé pour compatibilité
    return
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


@app.on_event("startup")
async def startup_event():
    """Initialisation de la base de données au démarrage"""
    await db.init_db()
    print("✅ Base de données initialisée")


@app.get("/health")
async def health(request: Request):
    """Endpoint de vérification de santé - accessible sans authentification"""
    return {"status": "ok", "sandbox": str(SANDBOX), "version": "2.3.0"}


# === ENDPOINT MÉTRIQUES PROMETHEUS ===
@app.get("/metrics")
def metrics(current_user: Optional[User] = Depends(optional_auth)):
    """Métriques Prometheus - authentification optionnelle"""
    if not NOX_METRICS_ENABLED:
        raise HTTPException(status_code=404, detail="metrics disabled")

    # mise à jour ponctuelle des métriques sandbox
    update_sandbox_metrics(str(SANDBOX))
    ct, payload = metrics_response()
    return Response(content=payload, media_type=ct)


# === UPLOAD DE FICHIERS ===
@app.post("/put")
def put(
    path: str, f: UploadFile = File(), current_user: User = Depends(get_current_user)
):
    """Upload de fichiers - authentification requise"""

    data = f.file.read()
    target = safe_join(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return {
        "message": f"Uploaded {len(data)} bytes to {path}",
        "user": current_user.email,
    }


# === EXÉCUTION PYTHON ===
class RunPy(BaseModel):
    code: str
    filename: str = "run.py"


@app.post("/run_py")
def run_py(
    body: RunPy, request: Request, current_user: User = Depends(get_current_user)
):
    """Exécution de code Python - authentification requise"""

    target = safe_join(body.filename)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body.code)

    try:
        proc = subprocess.run(
            ["python3", str(target)],
            cwd=str(SANDBOX),
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SEC,
        )
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "user": current_user.email,
        }

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Timeout")


# === EXÉCUTION SHELL ===
FORBIDDEN = {
    "rm",
    "reboot",
    "shutdown",
    "mkfs",
    "dd",
    "mount",
    "umount",
    "kill",
    "pkill",
    "sudo",
}


class RunSh(BaseModel):
    cmd: str


@app.post("/run_sh")
def run_sh(
    body: RunSh, request: Request, current_user: User = Depends(get_current_user)
):
    """Exécution de commandes shell - authentification requise"""

    parts = shlex.split(body.cmd)
    if not parts:
        raise HTTPException(status_code=400, detail="Empty command")
    if parts[0] in FORBIDDEN:
        raise HTTPException(status_code=400, detail="Forbidden command")

    try:
        proc = subprocess.run(
            parts, cwd=str(SANDBOX), capture_output=True, text=True, timeout=TIMEOUT_SEC
        )
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "user": current_user.email,
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Timeout")


# === LISTING DE FICHIERS ===
@app.get("/list")
def list_files(
    path: str = "",
    recursive: bool = False,
    current_user: User = Depends(get_current_user),
):
    """Listing des fichiers - authentification requise"""

    target = safe_join(path or ".")
    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    if target.is_file():
        stat = target.stat()
        return {
            "type": "file",
            "name": target.name,
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "user": current_user.email,
        }

    files = []
    pattern = "**/*" if recursive else "*"
    for item in sorted(target.glob(pattern)):
        try:
            stat = item.stat()
            files.append(
                {
                    "type": "file" if item.is_file() else "dir",
                    "name": str(item.relative_to(target)),
                    "size": stat.st_size if item.is_file() else None,
                    "modified": stat.st_mtime,
                }
            )
        except (OSError, ValueError):
            continue

    return {
        "type": "directory",
        "path": path,
        "files": files,
        "user": current_user.email,
    }


# === LECTURE DE FICHIERS ===
@app.get("/cat")
def cat(path: str, current_user: User = Depends(get_current_user)):
    """Lecture de fichiers - authentification requise"""

    target = safe_join(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    if not target.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    try:
        content = target.read_text(encoding="utf-8")
        return {"content": content, "user": current_user.email}
    except UnicodeDecodeError:
        content_bytes = target.read_bytes()
        return {
            "content": f"<binary file, {len(content_bytes)} bytes>",
            "user": current_user.email,
        }


# === SUPPRESSION DE FICHIERS ===
@app.delete("/delete")
def delete(path: str, current_user: User = Depends(get_current_user)):
    """Suppression de fichiers - authentification requise (admin uniquement via RoleChecker)"""

    # Vérification des permissions via le RoleChecker dans les dépendances
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403, detail="Only administrators can delete files"
        )

    target = safe_join(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    if target.is_file():
        target.unlink()
        return {"message": f"Deleted file {path}", "user": current_user.email}
    elif target.is_dir():
        import shutil

        shutil.rmtree(target)
        return {"message": f"Deleted directory {path}", "user": current_user.email}


# === ENDPOINTS ADMIN ===
@app.get("/admin/info")
def admin_info(current_user: User = Depends(get_current_user)):
    """Informations administrateur - admin uniquement"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    return {
        "message": "Admin endpoint accessible",
        "admin_user": current_user.email,
        "sandbox": str(SANDBOX),
        "metrics_enabled": NOX_METRICS_ENABLED,
    }


# === LANCEMENT DU SERVEUR ===
if __name__ == "__main__":
    import uvicorn

    host = os.getenv("NOX_BIND_ADDR", "127.0.0.1")
    port = int(os.getenv("NOX_PORT", "8081"))  # Port 8081 pour la version 2.3
    uvicorn.run(app, host=host, port=port)
