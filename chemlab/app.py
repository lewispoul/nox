"""Separate local application; does not load NOX execution/agent endpoints."""

import os
import secrets
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from chemlab.artifacts import (
    ArtifactStore,
    ArtifactUnavailable,
    MissingArtifact,
    DEFAULT_LIMIT,
)
from chemlab.artifact_routes import artifact_router

from chemlab.literature import Literature
from chemlab.models import (
    Device,
    Experiment,
    InventoryCalculation,
    Note,
    Observation,
    Project,
)
from chemlab.store import Conflict, Store, UnknownProject


def create_app(
    db_path=None,
    token=None,
    literature_path=None,
    artifact_root=None,
    artifact_limit=None,
):
    token = token or os.environ.get("CHEMLAB_TOKEN")
    if not token or len(token) < 24:
        raise RuntimeError(
            "Set CHEMLAB_TOKEN to a random value of at least 24 characters"
        )
    db_path = Path(db_path or os.environ.get("CHEMLAB_DB", ".run/chemlab.sqlite3"))
    selected_index = literature_path or os.environ.get("CHEMLAB_LITERATURE_INDEX")
    literature = Literature(Path(selected_index) if selected_index else None)
    store = Store(db_path)
    artifact_root = Path(
        artifact_root
        or os.environ.get("CHEMLAB_ARTIFACT_ROOT")
        or db_path.parent / (db_path.name + ".artifacts")
    )
    web_path = Path(__file__).parent / "web"
    if artifact_root.resolve().is_relative_to(web_path.resolve()):
        raise ValueError("Artifact storage must be outside the public UI directory")
    if artifact_limit is None:
        artifact_limit = int(os.environ.get("CHEMLAB_ARTIFACT_LIMIT", DEFAULT_LIMIT))
    artifacts = ArtifactStore(store, artifact_root, artifact_limit)

    def authorize(authorization: str | None = Header(default=None)):
        expected = "Bearer " + token
        if not authorization or not secrets.compare_digest(
            authorization.encode(), expected.encode()
        ):
            raise HTTPException(
                401, "Bearer token required", headers={"WWW-Authenticate": "Bearer"}
            )

    app = FastAPI(
        title="NOx local laboratory pilot",
        version="0.2.0",
        dependencies=[Depends(authorize)],
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.artifacts = artifacts
    app.include_router(artifact_router(artifacts))

    @app.exception_handler(MissingArtifact)
    async def missing_artifact(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=404)

    @app.exception_handler(ArtifactUnavailable)
    async def unavailable_artifact(request, exc):
        return JSONResponse({"detail": "Artifact storage unavailable"}, status_code=503)

    @app.exception_handler(Conflict)
    async def artifact_conflict(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.middleware("http")
    async def private_responses(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    # The shell contains no data or credentials. API routes retain the common
    # Bearer dependency; StaticFiles is deliberately mounted outside that layer.
    web_path = Path(__file__).parent / "web"
    if web_path.is_dir():
        app.mount("/ui", StaticFiles(directory=web_path, html=True), name="ui")

    def append(kind, value):
        try:
            return store.append(kind, value.model_dump(mode="json"))
        except Conflict as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "mode": "simulation_only",
            "literature_records": len(literature.records),
        }

    @app.get("/projects")
    def projects():
        return store.projects()

    @app.post("/projects")
    def add_project(project: Project):
        try:
            return store.add_project(project)
        except Conflict as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get("/experiments")
    def experiments(
        project_id: str | None = Query(default=None, pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    ):
        return store.experiments(project_id)

    @app.post("/experiments")
    def add_experiment(experiment: Experiment):
        try:
            return store.add_experiment(experiment)
        except Conflict as exc:
            raise HTTPException(409, str(exc)) from exc
        except UnknownProject as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.get("/experiments/{experiment_id}")
    def get_experiment(experiment_id: str):
        experiment = store.experiment(experiment_id)
        if experiment is None:
            raise HTTPException(404, "Unknown experiment")
        return experiment

    @app.get("/devices")
    def devices():
        return store.devices()

    @app.post("/devices")
    def add_device(device: Device):
        try:
            return store.add_device(device)
        except Conflict as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.post("/observations")
    def observe(observation: Observation):
        device = store.device(observation.device_id)
        if not device:
            raise HTTPException(404, "Unknown device")
        expected_unit = {"temperature.read": "degC", "mass.read_stable": "g"}[
            device["capability"]
        ]
        if observation.unit != expected_unit:
            raise HTTPException(422, "Unit does not match device capability")
        if device["capability"] == "mass.read_stable" and not observation.stable:
            raise HTTPException(422, "Stable mass reading required")
        return append("observation", observation)

    @app.post("/notes")
    def note(note: Note):
        return append("note", note)

    @app.get("/events")
    def events(
        experiment_id: str | None = Query(default=None, max_length=80),
        limit: int = Query(default=100, ge=1, le=500),
    ):
        return store.events(experiment_id, limit)

    @app.post("/inventory/calculate")
    def calculate(body: InventoryCalculation):
        if body.gross_g < body.tare_g:
            raise HTTPException(422, "Gross mass must be at least the tare")
        net = body.gross_g - body.tare_g
        return {
            "net_g": str(net),
            "volume_ml": str(net / body.density_g_ml) if body.density_g_ml else None,
            "quantity_status": (
                "estimated"
                if body.tare_kind == "estimated"
                else "calculated_from_measured_tare"
            ),
            "uncertainty_evaluated": False,
            "density_source": "user_supplied",
        }

    @app.get("/literature/search")
    def search(
        q: str = Query(min_length=1, max_length=500),
        limit: int = Query(default=5, ge=1, le=20),
    ):
        if not selected_index:
            raise HTTPException(503, "No literature export configured")
        try:
            return literature.search(q, limit)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    return app
