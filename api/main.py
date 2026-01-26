import logging

from fastapi import FastAPI

from api.routes import jobs
from api.routes import predict
from api.routes import agent

logger = logging.getLogger(__name__)

app = FastAPI(title="Nox API", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok"}


# branchement des routes
# Gracefully handle router registration failures to allow partial API functionality
# if some routes have initialization issues (e.g., missing dependencies)
try:
    app.include_router(jobs.router)
except Exception as e:
    logger.error(f"Failed to include jobs router: {e}", exc_info=True)

try:
    app.include_router(predict.router)
except Exception as e:
    logger.error(f"Failed to include predict router: {e}", exc_info=True)

try:
    app.include_router(agent.router)
except Exception as e:
    logger.error(f"Failed to include agent router: {e}", exc_info=True)
