import os
import pathlib
import shlex
import subprocess

# Import du middleware de sécurité Phase 2.1
import sys
import time

from fastapi import FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rate_limit_and_policy import RateLimitAndPolicyMiddleware

# Import des métriques Phase 2.2 - approche ChatGPT
sys.path.append(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "observability"
    )
)
from metrics_chatgpt import metrics_response, update_sandbox_metrics
from middleware import MetricsMiddleware

app = FastAPI(
    title="Nox API",
    description="API sécurisée d'exécution de code - Phase 2.2 avec Observabilité",
    version="2.2.0",
)

NOX_METRICS_ENABLED = os.getenv("NOX_METRICS_ENABLED", "1") == "1"

# Application des middlewares dans l'ordre recommandé par ChatGPT
app.add_middleware(MetricsMiddleware)
app.add_middleware(RateLimitAndPolicyMiddleware)

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
    """Endpoint de vérification de santé"""
    return {"status": "ok", "sandbox": str(SANDBOX)}


# === ENDPOINT MÉTRIQUES PROMETHEUS ===
@app.get("/metrics")
def metrics():
    if not NOX_METRICS_ENABLED:
        raise HTTPException(status_code=404, detail="metrics disabled")
    # mise à jour ponctuelle des métriques sandbox
    update_sandbox_metrics(os.getenv("NOX_SANDBOX", "/home/nox/nox/sandbox"))
    ct, payload = metrics_response()
    return Response(content=payload, media_type=ct)


# === UPLOAD DE FICHIERS ===
@app.post("/put")
async def put_file(
    path: str,
    request: Request,
    f: UploadFile = File(...),
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    """Upload un fichier dans le sandbox avec métriques"""
    check_auth(authorization)
    start_time = time.time()

    try:
        dest = safe_join(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        data = await f.read()
        dest.write_bytes(data)

        operation_time = time.time() - start_time
        metrics.track_http_request("POST", "/put", 200)
        metrics.track_file_operation("upload", operation_time, len(data))

        return {"saved": str(dest), "size": len(data)}
    except Exception as e:
        operation_time = time.time() - start_time
        metrics.track_http_request("POST", "/put", 500)
        metrics.track_file_operation("upload_failed", operation_time, 0)
        raise HTTPException(status_code=500, detail=str(e))


# === EXÉCUTION PYTHON ===
class RunPy(BaseModel):
    code: str
    filename: str = Field(default="run.py")


@app.post("/run_py")
async def run_py(
    body: RunPy,
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    """Exécute du code Python avec métriques"""
    check_auth(authorization)
    start_time = time.time()

    try:
        target = SANDBOX / body.filename
        target.write_text(body.code)

        proc = subprocess.run(
            ["python3", str(target)],
            cwd=str(SANDBOX),
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SEC,
        )

        execution_time = time.time() - start_time
        status = "success" if proc.returncode == 0 else "error"

        metrics.track_http_request(
            "POST", "/run_py", 200 if proc.returncode == 0 else 500
        )
        metrics.track_code_execution("python", status, execution_time)

        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }

    except subprocess.TimeoutExpired:
        execution_time = time.time() - start_time
        metrics.track_http_request("POST", "/run_py", 408)
        metrics.track_code_execution("python", "timeout", execution_time)
        raise HTTPException(status_code=408, detail="Timeout")
    except Exception as e:
        execution_time = time.time() - start_time
        metrics.track_http_request("POST", "/run_py", 500)
        metrics.track_code_execution("python", "failed", execution_time)
        raise HTTPException(status_code=500, detail=str(e))


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
async def run_sh(
    body: RunSh,
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    """Exécute une commande shell avec métriques"""
    check_auth(authorization)
    start_time = time.time()

    try:
        parts = shlex.split(body.cmd)
        if not parts:
            metrics.track_http_request("POST", "/run_sh", 400)
            raise HTTPException(status_code=400, detail="Empty command")
        if parts[0] in FORBIDDEN:
            metrics.track_http_request("POST", "/run_sh", 403)
            raise HTTPException(status_code=403, detail="Forbidden command")

        proc = subprocess.run(
            parts, cwd=str(SANDBOX), capture_output=True, text=True, timeout=TIMEOUT_SEC
        )

        execution_time = time.time() - start_time
        status = "success" if proc.returncode == 0 else "error"

        metrics.track_http_request(
            "POST", "/run_sh", 200 if proc.returncode == 0 else 500
        )
        metrics.track_code_execution("shell", status, execution_time)

        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }

    except subprocess.TimeoutExpired:
        execution_time = time.time() - start_time
        metrics.track_http_request("POST", "/run_sh", 408)
        metrics.track_code_execution("shell", "timeout", execution_time)
        raise HTTPException(status_code=408, detail="Timeout")
    except Exception as e:
        execution_time = time.time() - start_time
        metrics.track_http_request("POST", "/run_sh", 500)
        metrics.track_code_execution("shell", "failed", execution_time)
        raise HTTPException(status_code=500, detail=str(e))


# === GESTION DES FICHIERS ===
@app.get("/list")
async def list_files(
    path: str = "",
    request: Request = None,
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    """Liste les fichiers du sandbox avec métriques"""
    check_auth(authorization)

    try:
        target = safe_join(path) if path else SANDBOX
        if not target.exists():
            metrics.track_http_request("GET", "/list", 404)
            raise HTTPException(status_code=404, detail="Path not found")

        if target.is_file():
            metrics.track_http_request("GET", "/list", 200)
            return {"type": "file", "name": target.name, "size": target.stat().st_size}

        items = []
        for item in sorted(target.iterdir()):
            items.append(
                {
                    "name": item.name,
                    "type": "dir" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None,
                }
            )

        metrics.track_http_request("GET", "/list", 200)
        metrics.track_file_operation("list", 0, len(items))

        return {"type": "directory", "path": str(target), "items": items}
    except Exception as e:
        metrics.track_http_request("GET", "/list", 500)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get")
async def get_file(
    path: str,
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    """Récupère le contenu d'un fichier avec métriques"""
    check_auth(authorization)

    try:
        target = safe_join(path)
        if not target.exists() or not target.is_file():
            metrics.track_http_request("GET", "/get", 404)
            raise HTTPException(status_code=404, detail="File not found")

        content = target.read_text()

        metrics.track_http_request("GET", "/get", 200)
        metrics.track_file_operation("read", 0, len(content))

        return {"content": content, "size": len(content)}
    except Exception as e:
        metrics.track_http_request("GET", "/get", 500)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/delete")
async def delete_file(
    path: str,
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    """Supprime un fichier ou dossier avec métriques"""
    check_auth(authorization)

    try:
        target = safe_join(path)
        if not target.exists():
            metrics.track_http_request("DELETE", "/delete", 404)
            raise HTTPException(status_code=404, detail="Path not found")

        if target.is_file():
            target.unlink()
        else:
            import shutil

            shutil.rmtree(target)

        metrics.track_http_request("DELETE", "/delete", 200)
        metrics.track_file_operation("delete", 0, 1)

        return {"deleted": str(target)}
    except Exception as e:
        metrics.track_http_request("DELETE", "/delete", 500)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
