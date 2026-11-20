"""Separate local application; does not load NOX execution/agent endpoints."""
import os
import secrets
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query

from chemlab.literature import Literature
from chemlab.models import Device, InventoryCalculation, Note, Observation
from chemlab.store import Conflict, Store


def create_app(db_path=None, token=None, literature_path=None):
    token = token or os.environ.get("CHEMLAB_TOKEN")
    if not token or len(token) < 24:
        raise RuntimeError("Set CHEMLAB_TOKEN to a random value of at least 24 characters")
    db_path = Path(db_path or os.environ.get("CHEMLAB_DB", ".run/chemlab.sqlite3"))
    selected_index = literature_path or os.environ.get("CHEMLAB_LITERATURE_INDEX")
    literature = Literature(Path(selected_index) if selected_index else None)
    store = Store(db_path)

    def authorize(authorization: str | None = Header(default=None)):
        expected = "Bearer " + token
        if not authorization or not secrets.compare_digest(authorization.encode(), expected.encode()):
            raise HTTPException(401, "Bearer token required", headers={"WWW-Authenticate": "Bearer"})

    app = FastAPI(title="ChemLab local pilot", version="0.1.0",
                  dependencies=[Depends(authorize)], docs_url=None, redoc_url=None,
                  openapi_url=None)

    def append(kind, value):
        try:
            return store.append(kind, value.model_dump(mode="json"))
        except Conflict as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get("/health")
    def health():
        return {"status": "ok", "mode": "simulation_only", "literature_records": len(literature.records)}

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
        expected_unit = {"temperature.read": "degC", "mass.read_stable": "g"}[device["capability"]]
        if observation.unit != expected_unit:
            raise HTTPException(422, "Unit does not match device capability")
        if device["capability"] == "mass.read_stable" and not observation.stable:
            raise HTTPException(422, "Stable mass reading required")
        return append("observation", observation)

    @app.post("/notes")
    def note(note: Note):
        return append("note", note)

    @app.get("/events")
    def events(experiment_id: str | None = Query(default=None, max_length=80),
               limit: int = Query(default=100, ge=1, le=500)):
        return store.events(experiment_id, limit)

    @app.post("/inventory/calculate")
    def calculate(body: InventoryCalculation):
        if body.gross_g < body.tare_g:
            raise HTTPException(422, "Gross mass must be at least the tare")
        net = body.gross_g - body.tare_g
        return {"net_g": str(net),
                "volume_ml": str(net / body.density_g_ml) if body.density_g_ml else None,
                "quantity_status": "estimated" if body.tare_kind == "estimated" else "calculated_from_measured_tare",
                "uncertainty_evaluated": False, "density_source": "user_supplied"}

    @app.get("/literature/search")
    def search(q: str = Query(min_length=1, max_length=500), limit: int = Query(default=5, ge=1, le=20)):
        if not selected_index:
            raise HTTPException(503, "No literature export configured")
        try:
            return literature.search(q, limit)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    return app
