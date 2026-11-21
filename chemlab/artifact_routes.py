"""Authenticated artifact routes, mounted inside the pilot's common dependency."""

import hashlib
import os
from pathlib import Path
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Header, HTTPException, Path as ApiPath, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from chemlab.artifacts import ArtifactMetadata, ID_PATTERN

Identifier = Annotated[str, ApiPath(pattern=ID_PATTERN)]


def artifact_router(artifacts):
    router = APIRouter(prefix="/experiments/{experiment_id}/artifacts")

    @router.post("/{artifact_id}")
    async def upload(
        experiment_id: Identifier,
        artifact_id: Identifier,
        request: Request,
        x_artifact_metadata: Annotated[str, Header(max_length=8192)],
    ):
        try:
            metadata = ArtifactMetadata.model_validate_json(x_artifact_metadata)
        except (ValidationError, ValueError, RecursionError):
            raise HTTPException(422, "Invalid artifact metadata") from None
        await run_in_threadpool(artifacts.require_experiment, experiment_id)
        length = request.headers.get("content-length")
        if length is not None:
            try:
                declared = int(length)
                if declared < 0:
                    raise ValueError()
            except ValueError:
                raise HTTPException(422, "Invalid Content-Length") from None
            if declared > artifacts.limit:
                raise HTTPException(413, "Artifact exceeds configured byte limit")
        staged = artifacts.stage()
        filename = Path(staged.name)
        size = 0
        digest = hashlib.sha256()
        try:
            async for chunk in request.stream():
                size += len(chunk)
                if size > artifacts.limit:
                    raise HTTPException(413, "Artifact exceeds configured byte limit")
                digest.update(chunk)
                await run_in_threadpool(staged.write, chunk)
            if length is not None and size != declared:
                raise HTTPException(422, "Body length does not match Content-Length")
            staged.flush()
            os.fsync(staged.fileno())
            staged.close()
            payload, created = await run_in_threadpool(
                artifacts.publish,
                experiment_id,
                artifact_id,
                metadata,
                filename,
                digest.hexdigest(),
                size,
            )
            return JSONResponse(payload, status_code=201 if created else 200)
        finally:
            staged.close()
            filename.unlink(missing_ok=True)

    @router.get("")
    def listing(
        experiment_id: Identifier,
        limit: int = Query(default=100, ge=1, le=100),
        cursor: int = Query(default=0, ge=0),
    ):
        return artifacts.list(experiment_id, limit, cursor)

    @router.get("/{artifact_id}")
    def metadata(experiment_id: Identifier, artifact_id: Identifier):
        return artifacts.record(experiment_id, artifact_id)[1]

    @router.get("/{artifact_id}/content")
    def content(experiment_id: Identifier, artifact_id: Identifier):
        name, record = artifacts.record(experiment_id, artifact_id)
        handle = artifacts.open_object(name, record)

        def chunks():
            try:
                while chunk := handle.read(1024 * 1024):
                    yield chunk
            finally:
                handle.close()

        # Always download opaque bytes: uploaded HTML/SVG must never execute
        # under the origin serving the authenticated laboratory application.
        return StreamingResponse(
            chunks(),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": "attachment; filename*=UTF-8''"
                + quote(record["display_name"], safe=""),
                "Content-Length": str(record["byte_size"]),
                "Content-Security-Policy": "sandbox; default-src 'none'",
            },
        )

    return router
