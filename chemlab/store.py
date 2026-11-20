"""One connection per operation; transactions enforce durable idempotency."""
import json
from contextlib import contextmanager
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from chemlab.models import Device, Experiment, Project


class Conflict(ValueError):
    pass


class UnknownProject(ValueError):
    pass


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS devices (
                    id TEXT PRIMARY KEY, payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY, kind TEXT NOT NULL,
                    request TEXT NOT NULL, payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY, payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS experiments (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id),
                    payload TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS experiments_project_id
                    ON experiments(project_id);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def add_project(self, project: Project):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT payload FROM projects WHERE id=?", (project.id,)).fetchone()
            if row:
                if json.loads(row[0]) != project.model_dump():
                    raise Conflict("Project id already has a different configuration")
                return json.loads(row[0])
            db.execute("INSERT INTO projects VALUES (?,?)", (project.id, project.model_dump_json()))
        return project.model_dump()

    def projects(self):
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute("SELECT payload FROM projects ORDER BY id")]

    def add_experiment(self, experiment: Experiment):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT payload FROM experiments WHERE id=?", (experiment.id,)).fetchone()
            if row:
                if json.loads(row[0]) != experiment.model_dump():
                    raise Conflict("Experiment id already has a different configuration")
                return json.loads(row[0])
            if not db.execute("SELECT id FROM projects WHERE id=?", (experiment.project_id,)).fetchone():
                raise UnknownProject("Unknown project")
            db.execute("INSERT INTO experiments VALUES (?,?,?)",
                       (experiment.id, experiment.project_id, experiment.model_dump_json()))
        return experiment.model_dump()

    def experiments(self, project_id=None):
        with self.connect() as db:
            if project_id is None:
                rows = db.execute("SELECT payload FROM experiments ORDER BY id")
            else:
                rows = db.execute("SELECT payload FROM experiments WHERE project_id=? ORDER BY id", (project_id,))
            return [json.loads(row[0]) for row in rows]

    def experiment(self, experiment_id):
        with self.connect() as db:
            row = db.execute("SELECT payload FROM experiments WHERE id=?", (experiment_id,)).fetchone()
            return json.loads(row[0]) if row else None

    def add_device(self, device: Device):
        payload = device.model_dump_json()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT payload FROM devices WHERE id=?", (device.id,)).fetchone()
            if row:
                if json.loads(row[0]) != device.model_dump():
                    raise Conflict("Device id already has a different configuration")
                return json.loads(row[0])
            db.execute("INSERT INTO devices VALUES (?,?)", (device.id, payload))
        return device.model_dump()

    def devices(self):
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute("SELECT payload FROM devices ORDER BY id")]

    def device(self, device_id):
        with self.connect() as db:
            row = db.execute("SELECT payload FROM devices WHERE id=?", (device_id,)).fetchone()
            return json.loads(row[0]) if row else None

    def append(self, kind, request):
        serialized = json.dumps(request, sort_keys=True, ensure_ascii=False)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT kind, request, payload FROM events WHERE event_id=?", (request["event_id"],)).fetchone()
            if row:
                if row[0] != kind or row[1] != serialized:
                    raise Conflict("Event id already used with different content")
                return json.loads(row[2])
            payload = dict(request, kind=kind, recorded_at=datetime.now(timezone.utc).isoformat(),
                           source="simulated" if kind == "observation" else "manual",
                           status="recorded_local" if kind == "observation" else "draft_local")
            db.execute("INSERT INTO events VALUES (?,?,?,?)", (request["event_id"], kind, serialized, json.dumps(payload, ensure_ascii=False)))
        return payload

    def events(self, experiment_id=None, limit=100):
        with self.connect() as db:
            # Experiment is a JSON property; no interpolation of caller input.
            sql = "SELECT payload FROM events"
            params = []
            if experiment_id is not None:
                sql += " WHERE json_extract(request, '$.experiment_id') = ?"
                params.append(experiment_id)
            sql += " ORDER BY rowid DESC LIMIT ?"
            params.append(limit)
            return [json.loads(row[0]) for row in db.execute(sql, params)]
