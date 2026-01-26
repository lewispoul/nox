from fastapi import FastAPI

from api.routes import jobs
from api.routes import predict
from api.routes import agent

app = FastAPI(title="Nox API", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok"}


# branchement des routes
try:
    app.include_router(jobs.router)
except Exception:
    # Intentionally ignore failures when including optional 'jobs' routes.
    pass

try:
    app.include_router(predict.router)
except Exception:
    # Intentionally ignore failures when including optional 'predict' routes.
    pass

try:
    app.include_router(agent.router)
except Exception:
    # Intentionally ignore failures when including optional 'agent' routes.
    pass
