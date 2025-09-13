import os
import pathlib
import shlex
import subprocess
import sys

# Solution rapide ChatGPT pour les imports
from pathlib import Path

from fastapi import FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.sessions import SessionMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

# ROOT = nox-api-src/
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from observability.metrics_chatgpt import metrics_response, update_sandbox_metrics
from observability.middleware import MetricsMiddleware

# OAuth2 imports
try:
    from auth.oauth2_config import oauth2_settings
    from auth.oauth2_endpoints import router as oauth2_router

    OAUTH2_AVAILABLE = True
except ImportError:
    OAUTH2_AVAILABLE = False

app = FastAPI(
    title="Nox API",
    description="API sécurisée d'exécution de code - Phase 2.4 avec OAuth2",
    version="2.4.0",
)

NOX_METRICS_ENABLED = os.getenv("NOX_METRICS_ENABLED", "1") == "1"

# Add session middleware for OAuth2
if OAUTH2_AVAILABLE:
    app.add_middleware(
        SessionMiddleware,
        secret_key=os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production"),
        max_age=3600,  # 1 hour
    )

# Application des middlewares - temporairement sans sécurité pour test
app.add_middleware(MetricsMiddleware)
# app.add_middleware(RateLimitAndPolicyMiddleware)  # Désactivé temporairement

# Include OAuth2 routes if available
if OAUTH2_AVAILABLE:
    app.include_router(oauth2_router)


# Add OAuth2 status endpoint
@app.get("/auth/status")
async def auth_status():
    """Get authentication system status"""
    return {
        "oauth2_enabled": OAUTH2_AVAILABLE,
        "providers_configured": (
            oauth2_settings.any_provider_enabled if OAUTH2_AVAILABLE else False
        ),
        "jwt_auth_available": True,
        "version": "2.4.0",
    }


NOX_TOKEN = os.getenv("NOX_API_TOKEN", "").strip()
SANDBOX = pathlib.Path(os.getenv("NOX_SANDBOX", "/home/nox/nox/sandbox")).resolve()
TIMEOUT_SEC = int(os.getenv("NOX_TIMEOUT", "20"))

SANDBOX.mkdir(parents=True, exist_ok=True)


def check_auth(auth: str | None):
    # Désactivé temporairement pour test
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


@app.get("/health")
async def health(request: Request):
    """Endpoint de vérification de santé"""
    return {"status": "ok", "sandbox": str(SANDBOX)}


# === ENDPOINT MÉTRIQUES PROMETHEUS ===
@app.get("/metrics")
def metrics():
    if not NOX_METRICS_ENABLED:
        raise HTTPException(status_code=404, detail="metrics disabled")
    # mise à jour ponctuelle des métriques sandbox
    update_sandbox_metrics(str(SANDBOX))
    ct, payload = metrics_response()
    return Response(content=payload, media_type=ct)


# === UPLOAD DE FICHIERS ===
@app.post("/put")
def put(
    path: str,
    f: UploadFile = File(),
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    check_auth(authorization)

    data = f.file.read()
    target = safe_join(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return {"message": f"Uploaded {len(data)} bytes to {path}"}


# === EXÉCUTION PYTHON ===
class RunPy(BaseModel):
    code: str
    filename: str = "run.py"


@app.post("/run_py")
def run_py(
    body: RunPy,
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    check_auth(authorization)

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
    body: RunSh,
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    check_auth(authorization)

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
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Timeout")


# === LISTING DE FICHIERS ===
@app.get("/list")
def list_files(
    path: str = "",
    recursive: bool = False,
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    check_auth(authorization)

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

    return {"type": "directory", "path": path, "files": files}


# === LECTURE DE FICHIERS ===
@app.get("/cat")
def cat(
    path: str, authorization: str | None = Header(default=None, alias="Authorization")
):
    check_auth(authorization)

    target = safe_join(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    if not target.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    try:
        content = target.read_text(encoding="utf-8")
        return {"content": content}
    except UnicodeDecodeError:
        content_bytes = target.read_bytes()
        return {"content": f"<binary file, {len(content_bytes)} bytes>"}


# === SUPPRESSION DE FICHIERS ===
@app.delete("/delete")
def delete(
    path: str, authorization: str | None = Header(default=None, alias="Authorization")
):
    check_auth(authorization)

    target = safe_join(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    if target.is_file():
        target.unlink()
        return {"message": f"Deleted file {path}"}
    elif target.is_dir():
        import shutil

        shutil.rmtree(target)
        return {"message": f"Deleted directory {path}"}


# === LANCEMENT DU SERVEUR ===
if __name__ == "__main__":
    import uvicorn

    host = os.getenv("NOX_BIND_ADDR", "127.0.0.1")
    port = int(os.getenv("NOX_PORT", "8080"))
    uvicorn.run(app, host=host, port=port)
