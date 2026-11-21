import hashlib
from contextlib import contextmanager
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import threading

from fastapi.testclient import TestClient
import pytest

from chemlab.app import create_app
from chemlab.artifacts import ArtifactUnavailable, HARD_LIMIT

TOKEN = "artifact-tests-token-at-least-24-characters"
BASE = "/experiments/E/artifacts"


def open_client(tmp_path, **kwargs):
    return TestClient(
        create_app(tmp_path / "pilot.sqlite3", TOKEN, **kwargs),
        headers={"Authorization": "Bearer " + TOKEN},
    )


@pytest.fixture
def client(tmp_path):
    with open_client(tmp_path) as client:
        client.post("/projects", json={"id": "P", "name": "Project"}).raise_for_status()
        for identifier in ("E", "OTHER"):
            client.post(
                "/experiments",
                json={"id": identifier, "project_id": "P", "name": identifier},
            ).raise_for_status()
        yield client


def upload(client, identifier="A", body=b"original bytes", metadata=None, base=BASE):
    metadata = metadata or {"display_name": "original.fid"}
    return client.post(
        f"{base}/{identifier}",
        content=body,
        headers={"X-Artifact-Metadata": json.dumps(metadata)},
    )


def test_round_trip_restart_retry_and_download_headers(client, tmp_path):
    body = b"<svg><script>alert(1)</script></svg>\x00\xff"
    metadata = {"display_name": "spectrum.svg", "media_type": "image/svg+xml"}
    created = upload(client, body=body, metadata=metadata)
    assert created.status_code == 201, created.text
    record = created.json()
    assert record["sha256"] == hashlib.sha256(body).hexdigest()
    assert record["byte_size"] == len(body)
    assert "object_name" not in record
    with open_client(tmp_path) as restarted:
        retry = upload(restarted, body=body, metadata=metadata)
        assert retry.status_code == 200
        assert retry.json() == record
        assert restarted.get(BASE + "/A").json() == record
        response = restarted.get(BASE + "/A/content")
        assert response.content == body
        assert response.headers["content-type"] == "application/octet-stream"
        assert response.headers["content-disposition"].startswith("attachment;")
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert "sandbox" in response.headers["content-security-policy"]
    assert len(list(client.app.state.artifacts.objects.iterdir())) == 1
    assert not list(client.app.state.artifacts.staging.iterdir())


@pytest.mark.parametrize(
    "method,path",
    [
        ("POST", BASE + "/A"),
        ("GET", BASE),
        ("GET", BASE + "/A"),
        ("GET", BASE + "/A/content"),
    ],
)
def test_authentication_on_every_route(client, method, path):
    assert (
        client.request(method, path, headers={"Authorization": ""}).status_code == 401
    )


def test_unknown_and_mismatched_experiments_conflicts(client):
    assert upload(client, base="/experiments/MISSING/artifacts").status_code == 404
    assert client.get("/experiments/MISSING/artifacts").status_code == 404
    original = upload(client).json()
    assert upload(client, body=b"changed").status_code == 409
    assert upload(client, metadata={"display_name": "changed"}).status_code == 409
    assert upload(client, base="/experiments/OTHER/artifacts").status_code == 409
    assert client.get("/experiments/OTHER/artifacts/A").status_code == 404
    assert client.get("/experiments/OTHER/artifacts/A/content").status_code == 404
    assert client.get(BASE + "/A").json() == original


@pytest.mark.parametrize(
    "name",
    [
        "../private",
        "a/b",
        "a\\b",
        "C:secret",
        "a\n.txt",
        "a\x00.txt",
        "..",
        "\nname",
        "name\x85",
    ],
)
def test_unsafe_names_are_rejected(client, name):
    assert upload(client, metadata={"display_name": name}).status_code == 422


def test_invalid_metadata_and_ids(client):
    for metadata in (
        {"display_name": "ok", "unexpected": 1},
        {"display_name": "ok", "media_type": "text/html\r\nX-Test: yes"},
        {"display_name": "ok", "kind": "derived"},
    ):
        assert upload(client, metadata=metadata).status_code == 422
    assert (
        client.post(
            BASE + "/A", content=b"x", headers={"X-Artifact-Metadata": "not JSON"}
        ).status_code
        == 422
    )
    assert upload(client, identifier="bad.id").status_code == 422
    assert client.get(BASE + "?limit=101").status_code == 422
    assert client.get(BASE + "?cursor=-1").status_code == 422


def test_limits_with_and_without_content_length(client):
    client.app.state.artifacts.limit = 4
    assert upload(client, body=b"1234").status_code == 201
    assert upload(client, identifier="B", body=b"12345").status_code == 413

    def chunks():
        yield b"12"
        yield b"345"

    response = client.post(
        BASE + "/C",
        content=chunks(),
        headers={"X-Artifact-Metadata": '{"display_name":"chunked"}'},
    )
    assert response.status_code == 413
    assert len(client.get(BASE).json()["items"]) == 1
    assert not list(client.app.state.artifacts.staging.iterdir())


def test_concurrent_duplicate_uploads_and_recovery(client):
    with ThreadPoolExecutor(max_workers=6) as pool:
        responses = list(pool.map(lambda _: upload(client), range(6)))
    assert sorted(r.status_code for r in responses) == [200] * 5 + [201]
    assert len({r.json()["created_at"] for r in responses}) == 1
    assert len(list(client.app.state.artifacts.objects.iterdir())) == 1
    assert client.app.state.artifacts.recover() == 0


def test_provenance_parents_and_pagination(client):
    upload(client)
    provenance = {
        "tool": "synthetic",
        "tool_version": "1",
        "recipe_version": "1",
        "execution_mode": "simulated",
        "parameters": {"x": 2},
        "units": {"x": "g"},
    }
    metadata = {
        "display_name": "result.json",
        "kind": "derived",
        "parent_artifact_ids": ["A"],
        "provenance": provenance,
    }
    assert upload(client, "B", metadata=metadata).status_code == 201
    assert (
        upload(
            client, "C", metadata=dict(metadata, parent_artifact_ids=["C"])
        ).status_code
        == 409
    )
    assert (
        upload(
            client, "C", metadata=dict(metadata, parent_artifact_ids=["MISSING"])
        ).status_code
        == 409
    )
    assert (
        upload(
            client, "C", metadata=metadata, base="/experiments/OTHER/artifacts"
        ).status_code
        == 409
    )
    first = client.get(BASE + "?limit=1").json()
    assert [x["artifact_id"] for x in first["items"]] == ["A"]
    upload(client, "C")
    rest = client.get(BASE + "?cursor=" + str(first["next_cursor"])).json()
    assert [x["artifact_id"] for x in rest["items"]] == ["B", "C"]
    assert rest["next_cursor"] is None


def test_failure_before_and_after_publication_has_no_committed_record(
    client, monkeypatch
):
    artifacts = client.app.state.artifacts
    import chemlab.artifacts as module

    real_replace = module.os.replace

    def fail(*args):
        raise OSError("synthetic rename failure")

    monkeypatch.setattr(module.os, "replace", fail)
    with pytest.raises(OSError):
        upload(client)
    assert client.get(BASE).json()["items"] == []
    assert not list(artifacts.staging.iterdir())
    monkeypatch.setattr(module.os, "replace", real_replace)
    # Fault after publication but before metadata commit.
    with artifacts.store.connect() as db:
        db.execute(
            "CREATE TRIGGER fail_artifact BEFORE INSERT ON artifacts BEGIN SELECT RAISE(ABORT, 'synthetic insert failure'); END"
        )
    with pytest.raises(sqlite3.IntegrityError):
        upload(client)
    assert client.get(BASE).json()["items"] == []
    assert len(list(artifacts.objects.iterdir())) == 1
    assert artifacts.recover() == 1
    with artifacts.store.connect() as db:
        db.execute("DROP TRIGGER fail_artifact")
    assert upload(client).status_code == 201


def test_recovery_cannot_delete_inflight_or_committed_objects(client, monkeypatch):
    artifacts = client.app.state.artifacts
    import chemlab.artifacts as module

    real_replace = module.os.replace
    published, release = threading.Event(), threading.Event()

    def pause(source, destination):
        real_replace(source, destination)
        published.set()
        assert release.wait(5)

    monkeypatch.setattr(module.os, "replace", pause)
    active_stage = artifacts.stage()
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            uploading = pool.submit(upload, client)
            assert published.wait(5)
            recovering = pool.submit(artifacts.recover)
            release.set()
            assert uploading.result().status_code == 201
            assert recovering.result() == 0
        assert Path(active_stage.name).exists()
        assert client.get(BASE + "/A/content").status_code == 200
    finally:
        release.set()
        active_stage.close()
        Path(active_stage.name).unlink(missing_ok=True)


def test_missing_or_corrupt_bytes_fail_closed(client):
    upload(client)
    artifact = next(client.app.state.artifacts.objects.iterdir())
    artifact.write_bytes(b"corrupt")
    assert client.get(BASE + "/A/content").status_code == 503
    assert upload(client).status_code == 503
    artifact.unlink()
    assert client.get(BASE + "/A/content").status_code == 503


def test_storage_is_not_static_and_links_are_rejected(client, tmp_path):
    upload(client)
    assert client.get("/ui/artifacts/A/content").status_code == 404
    assert client.get(
        "/ui/../" + client.app.state.artifacts.objects.name
    ).status_code in (401, 404)
    public = Path(__file__).resolve().parents[2] / "chemlab" / "web"
    with pytest.raises(ValueError, match="public UI"):
        create_app(tmp_path / "other.sqlite3", TOKEN, artifact_root=public / "uploads")
    link = tmp_path / "linked-storage"
    try:
        link.symlink_to(client.app.state.artifacts.root, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation not permitted on this host")
    with pytest.raises(ArtifactUnavailable):
        create_app(tmp_path / "other.sqlite3", TOKEN, artifact_root=link)


@pytest.mark.parametrize("limit", [0, -1, HARD_LIMIT + 1, True])
def test_config_limits(tmp_path, limit):
    with pytest.raises(ValueError):
        create_app(tmp_path / "pilot.sqlite3", TOKEN, artifact_limit=limit)


def test_failed_commit_rolls_back_metadata_and_recovers_blob(
    client, monkeypatch, tmp_path
):
    store = client.app.state.artifacts.store
    connect = store.connect

    @contextmanager
    def failed_commit():
        with connect() as db:
            yield db
            if (
                db.in_transaction
                and db.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
            ):
                raise sqlite3.OperationalError("synthetic commit failure")

    monkeypatch.setattr(store, "connect", failed_commit)
    with pytest.raises(sqlite3.OperationalError):
        upload(client)
    monkeypatch.setattr(store, "connect", connect)
    with open_client(tmp_path) as restarted:
        assert restarted.get(BASE).json()["items"] == []
        assert restarted.app.state.artifacts.recover() == 1
        assert upload(restarted).status_code == 201


def test_artifact_root_cannot_be_shared_by_different_databases(client, tmp_path):
    upload(client)
    with pytest.raises(ValueError, match="different database"):
        create_app(
            tmp_path / "different.sqlite3",
            TOKEN,
            artifact_root=client.app.state.artifacts.root,
        )
    assert client.app.state.artifacts.recover() == 0
    assert client.get(BASE + "/A/content").content == b"original bytes"


def test_interrupted_body_leaves_no_record_or_staged_content(client):
    def interrupted():
        yield b"partial"
        raise RuntimeError("synthetic transport interruption")

    with pytest.raises(Exception):
        client.post(
            BASE + "/A",
            content=interrupted(),
            headers={"X-Artifact-Metadata": '{"display_name":"interrupted"}'},
        )
    assert client.get(BASE).json()["items"] == []
    assert not list(client.app.state.artifacts.staging.iterdir())


def test_symlinked_object_does_not_escape_private_storage(client, tmp_path):
    upload(client)
    obj = next(client.app.state.artifacts.objects.iterdir())
    external = tmp_path / "external"
    external.write_bytes(b"original bytes")
    obj.unlink()
    try:
        obj.symlink_to(external)
    except OSError:
        pytest.skip("Symlink creation not permitted on this host")
    assert client.get(BASE + "/A/content").status_code == 503
    with pytest.raises(ArtifactUnavailable):
        client.app.state.artifacts.recover()
    assert external.read_bytes() == b"original bytes"
