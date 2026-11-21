"""Immutable experiment artifacts. SQLite serializes publication and recovery."""

import hashlib
from contextlib import closing
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import unicodedata
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field, field_validator, model_validator

from chemlab.models import StrictModel
from chemlab.store import Conflict

DEFAULT_LIMIT = 25 * 1024 * 1024
HARD_LIMIT = 256 * 1024 * 1024
ID_PATTERN = r"^[a-zA-Z0-9_-]{1,80}$"


class MissingArtifact(ValueError):
    pass


class ArtifactUnavailable(ValueError):
    pass


class Provenance(StrictModel):
    tool: str = Field(min_length=1, max_length=80)
    tool_version: str = Field(min_length=1, max_length=80)
    recipe_version: str = Field(min_length=1, max_length=80)
    execution_mode: Literal["manual", "calculated", "simulated"]
    parameters: dict[str, Any]
    units: dict[str, str]
    data_sources: list[dict[str, Any]] = Field(default_factory=list, max_length=32)


class ArtifactMetadata(StrictModel):
    display_name: str = Field(min_length=1, max_length=160)
    media_type: str = Field(
        default="application/octet-stream",
        pattern=r"^[a-zA-Z0-9!#$&^_.+-]+/[a-zA-Z0-9!#$&^_.+-]+$",
        max_length=120,
    )
    kind: Literal["original", "calculation", "derived"] = "original"
    parent_artifact_ids: list[str] = Field(default_factory=list, max_length=32)
    provenance: Provenance | None = None

    @field_validator("display_name", mode="before")
    @classmethod
    def safe_name(cls, value):
        if not isinstance(value, str):
            return value
        if value.strip() in {".", ".."} or any(
            unicodedata.category(c).startswith("C") or c in "/\\:" for c in value
        ):
            raise ValueError("Display name must not contain paths or controls")
        return value

    @field_validator("parent_artifact_ids")
    @classmethod
    def valid_parents(cls, values):
        if len(values) != len(set(values)) or any(
            not re.fullmatch(ID_PATTERN, value) for value in values
        ):
            raise ValueError("Parents must be unique artifact identifiers")
        return values

    @model_validator(mode="after")
    def consistent_kind(self):
        if self.kind == "original" and self.parent_artifact_ids:
            raise ValueError("Originals have no parents")
        if self.kind != "original" and self.provenance is None:
            raise ValueError("Calculation and derived artifacts require provenance")
        if self.kind == "derived" and not self.parent_artifact_ids:
            raise ValueError("Derived artifacts require parents")
        # Parameters/data sources may be nested JSON, but never NaN/Infinity.
        json.dumps(self.model_dump(), allow_nan=False)
        return self


def check_path(path):
    """Reject symlinks/junctions, including ancestors, in local managed storage."""
    path = Path(path).absolute()
    for part in (path, *path.parents):
        if part.is_symlink() or getattr(part, "is_junction", lambda: False)():
            raise ArtifactUnavailable("Artifact storage must not use links")
    return path


class ArtifactStore:
    def __init__(self, store, root, limit=DEFAULT_LIMIT):
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 0 < limit <= HARD_LIMIT
        ):
            raise ValueError(f"Artifact limit must be 1..{HARD_LIMIT} bytes")
        self.store = store
        self.root = check_path(root)
        self.objects = self.root / "objects"
        self.staging = self.root / "staging"
        self.limit = limit
        for directory in (self.root, self.objects, self.staging):
            check_path(directory).mkdir(parents=True, exist_ok=True)
        # Recovery is scoped to exactly one database. Misconfiguring two pilots
        # with a shared artifact root must never delete the other pilot's data.
        owner_path = check_path(self.root / "owner.sqlite3")
        with closing(sqlite3.connect(owner_path, timeout=10)) as owner, owner:
            owner.execute(
                "CREATE TABLE IF NOT EXISTS owner (id INTEGER PRIMARY KEY, database_path TEXT NOT NULL)"
            )
            identity = str(store.path.resolve())
            owner.execute("INSERT OR IGNORE INTO owner VALUES (1, ?)", (identity,))
            if (
                owner.execute("SELECT database_path FROM owner WHERE id=1").fetchone()[
                    0
                ]
                != identity
            ):
                raise ValueError("Artifact root belongs to a different database")
        with store.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS artifacts (
                artifact_id TEXT PRIMARY KEY,
                experiment_id TEXT NOT NULL REFERENCES experiments(id),
                object_name TEXT NOT NULL UNIQUE,
                payload TEXT NOT NULL
            )""")
            db.execute(
                "CREATE INDEX IF NOT EXISTS artifacts_experiment ON artifacts(experiment_id)"
            )

    def stage(self):
        check_path(self.staging)
        return tempfile.NamedTemporaryFile(mode="w+b", dir=self.staging, delete=False)

    def require_experiment(self, experiment_id):
        if self.store.experiment(experiment_id) is None:
            raise MissingArtifact("Unknown experiment")

    def publish(self, experiment_id, artifact_id, metadata, staged, digest, size):
        self.require_experiment(experiment_id)
        request = metadata.model_dump(mode="json")
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT experiment_id, object_name, payload FROM artifacts WHERE artifact_id=?",
                (artifact_id,),
            ).fetchone()
            if row:
                existing = json.loads(row[2])
                if (
                    row[0] != experiment_id
                    or any(existing[k] != v for k, v in request.items())
                    or existing["sha256"] != digest
                    or existing["byte_size"] != size
                ):
                    raise Conflict(
                        "Artifact id already has different content or metadata"
                    )
                # A retry must not confirm metadata whose bytes are missing/corrupt.
                with self.open_object(row[1], existing):
                    pass
                return existing, False
            if artifact_id in metadata.parent_artifact_ids:
                raise Conflict("Artifact cannot be its own parent")
            for parent in metadata.parent_artifact_ids:
                parent_row = db.execute(
                    "SELECT experiment_id FROM artifacts WHERE artifact_id=?", (parent,)
                ).fetchone()
                if not parent_row or parent_row[0] != experiment_id:
                    raise Conflict("Parent must exist in the same experiment")
            # Parents must already exist and records cannot be updated: cycles
            # cannot be introduced into this append-only graph.
            object_name = uuid4().hex
            destination = check_path(self.objects / object_name)
            if destination.exists():
                raise ArtifactUnavailable("Object identifier collision")
            payload = dict(
                request,
                schema_version=1,
                artifact_id=artifact_id,
                experiment_id=experiment_id,
                sha256=digest,
                byte_size=size,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            os.replace(staged, destination)
            if os.name != "nt":
                descriptor = os.open(self.objects, os.O_RDONLY)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
            # If insertion/commit fails, an unreferenced complete blob may remain.
            # Recovery uses the SAME database write lock, so cannot race publication.
            db.execute(
                "INSERT INTO artifacts VALUES (?,?,?,?)",
                (
                    artifact_id,
                    experiment_id,
                    object_name,
                    json.dumps(payload, allow_nan=False),
                ),
            )
        return payload, True

    def record(self, experiment_id, artifact_id):
        with self.store.connect() as db:
            row = db.execute(
                "SELECT object_name, payload FROM artifacts WHERE experiment_id=? AND artifact_id=?",
                (experiment_id, artifact_id),
            ).fetchone()
        if row is None:
            raise MissingArtifact("Unknown artifact")
        return row[0], json.loads(row[1])

    def list(self, experiment_id, limit=100, cursor=0):
        self.require_experiment(experiment_id)
        with self.store.connect() as db:
            rows = db.execute(
                "SELECT rowid, payload FROM artifacts WHERE experiment_id=? AND rowid>? ORDER BY rowid LIMIT ?",
                (experiment_id, cursor, limit + 1),
            ).fetchall()
        return {
            "items": [json.loads(row[1]) for row in rows[:limit]],
            "next_cursor": rows[limit - 1][0] if len(rows) > limit else None,
        }

    def open_object(self, name, metadata):
        if not re.fullmatch(r"[a-f0-9]{32}", name):
            raise ArtifactUnavailable("Invalid stored object")
        handle = None
        try:
            handle = check_path(self.objects / name).open("rb")
            if os.fstat(handle.fileno()).st_size != metadata["byte_size"]:
                raise ArtifactUnavailable("Artifact size check failed")
            digest = hashlib.sha256()
            size = 0
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
            if (
                digest.hexdigest() != metadata["sha256"]
                or size != metadata["byte_size"]
            ):
                raise ArtifactUnavailable("Artifact integrity check failed")
            handle.seek(0)
            return handle
        except (OSError, ArtifactUnavailable) as exc:
            if handle:
                handle.close()
            raise ArtifactUnavailable("Artifact content unavailable") from exc

    def recover(self):
        """Remove only unreferenced finalized objects; never touch active staging.

        Crash-left staging is retained for explicit offline maintenance. There
        is no safe time-based deletion of files another process may be uploading.
        """
        removed = 0
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            referenced = {
                row[0] for row in db.execute("SELECT object_name FROM artifacts")
            }
            for path in check_path(self.objects).iterdir():
                check_path(path)
                if (
                    re.fullmatch(r"[a-f0-9]{32}", path.name)
                    and path.name not in referenced
                ):
                    path.unlink()
                    removed += 1
        return removed
