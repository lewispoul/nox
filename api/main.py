from fastapi import FastAPI

from api.routes import jobs  # sera présent après création de jobs.py

app = FastAPI(title="Nox API", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok"}


# branchement des routes
try:
    app.include_router(jobs.router)
except Exception:
    pass
