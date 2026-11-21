from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from chemlab.app import create_app
from chemlab.models import Experiment, Project
from chemlab.store import Store

TOKEN = "project-tests-token-at-least-24-characters"


def client_for(path):
    return TestClient(
        create_app(path, TOKEN), headers={"Authorization": "Bearer " + TOKEN}
    )


@pytest.fixture
def client(tmp_path):
    with client_for(tmp_path / "registry.sqlite3") as client:
        yield client


def test_project_and_experiment_persist_and_retry(tmp_path):
    path = tmp_path / "persistent.sqlite3"
    project = {"id": "OLED", "name": "OLED project"}
    experiment = {"id": "LPP-26-050", "project_id": "OLED", "name": "Test synthesis"}
    with client_for(path) as client:
        assert client.post("/projects", json=project).json() == project
        assert client.post("/experiments", json=experiment).json() == experiment
    with client_for(path) as client:
        assert client.get("/projects").json() == [project]
        assert client.get("/experiments/LPP-26-050").json() == experiment
        assert client.post("/projects", json=project).json() == project
        assert client.post("/experiments", json=experiment).json() == experiment
        assert client.get("/experiments").json() == [experiment]


def test_registry_conflicts_do_not_overwrite(client):
    project = {"id": "P", "name": "Original"}
    experiment = {"id": "E", "project_id": "P", "name": "Original experiment"}
    client.post("/projects", json=project)
    client.post("/experiments", json=experiment)
    assert (
        client.post("/projects", json=dict(project, name="Changed")).status_code == 409
    )
    assert (
        client.post("/experiments", json=dict(experiment, name="Changed")).status_code
        == 409
    )
    assert (
        client.post(
            "/experiments", json=dict(experiment, project_id="OTHER")
        ).status_code
        == 409
    )
    assert client.get("/projects").json() == [project]
    assert client.get("/experiments/E").json() == experiment


def test_project_required_and_filter_is_exact(client):
    experiment = {"id": "E", "project_id": "P", "name": "Experiment"}
    assert client.post("/experiments", json=experiment).status_code == 404
    assert client.get("/experiments").json() == []
    for project_id in ("P", "P2"):
        client.post("/projects", json={"id": project_id, "name": project_id})
        client.post(
            "/experiments",
            json=dict(experiment, id="E-" + project_id, project_id=project_id),
        )
    assert [x["id"] for x in client.get("/experiments?project_id=P").json()] == ["E-P"]
    assert client.get("/experiments?project_id=UNKNOWN").json() == []
    assert client.get("/experiments/UNKNOWN").status_code == 404


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/projects"),
        ("POST", "/projects"),
        ("GET", "/experiments"),
        ("POST", "/experiments"),
        ("GET", "/experiments/ANY"),
    ],
)
def test_registry_requires_authentication(client, method, path):
    assert (
        client.request(
            method, path, headers={"Authorization": "Bearer wrong"}
        ).status_code
        == 401
    )


def test_registry_rejects_invalid_identifiers_and_fields(client):
    for payload in (
        {"id": "bad/id", "name": "Bad"},
        {"id": "P", "name": " "},
        {"id": "P", "name": "Project", "owner": "invented"},
    ):
        assert client.post("/projects", json=payload).status_code == 422
    client.post("/projects", json={"id": "P", "name": "Project"})
    for changes in ({"id": "bad/id"}, {"project_id": "bad id"}, {"name": ""}):
        payload = dict(id="E", project_id="P", name="Experiment")
        payload.update(changes)
        assert client.post("/experiments", json=payload).status_code == 422
    assert client.get("/experiments?project_id=bad%20id").status_code == 422


def test_legacy_notes_need_no_registered_experiment(client):
    response = client.post(
        "/notes",
        json={
            "event_id": "old-note",
            "experiment_id": "UNREGISTERED",
            "text": "Legacy",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "draft_local"
    assert client.get("/experiments").json() == []
    assert len(client.get("/events?experiment_id=UNREGISTERED").json()) == 1


def test_concurrent_registry_retries_remain_single_records(tmp_path):
    store = Store(tmp_path / "concurrent.sqlite3")
    project = Project(id="P", name="Project")
    experiment = Experiment(id="E", project_id="P", name="Experiment")
    with ThreadPoolExecutor(max_workers=8) as pool:
        project_results = list(
            pool.map(lambda _: store.add_project(project), range(20))
        )
        experiment_results = list(
            pool.map(lambda _: store.add_experiment(experiment), range(20))
        )
    assert all(x == project.model_dump() for x in project_results)
    assert all(x == experiment.model_dump() for x in experiment_results)
    assert len(store.projects()) == len(store.experiments()) == 1
