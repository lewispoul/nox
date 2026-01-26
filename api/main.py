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
    # Ignore if router is not available
    pass

try:
    app.include_router(predict.router)
except Exception:
    # Ignore if router is not available
    pass

try:
    app.include_router(agent.router)
except Exception:
    # Ignore if router is not available
    pass
