"""Integration boundaries: public shell, private records, no cached responses."""

from fastapi.testclient import TestClient
from chemlab.app import create_app

TOKEN = "testing-token-at-least-24-characters"


def test_public_shell_has_no_data_and_api_stays_private(tmp_path):
    with TestClient(create_app(tmp_path / "ui.sqlite3", TOKEN)) as client:
        response = client.get("/ui/")
        assert response.status_code == 200
        assert "NOx" in response.text
        assert TOKEN not in response.text
        assert response.headers["cache-control"] == "no-store"
        for route in ("/health", "/projects", "/experiments", "/events", "/devices"):
            assert client.get(route).status_code == 401
        assert client.post("/notes", json={"text": "unauthorized"}).status_code == 401
        assert client.get("/ui/app.js").status_code == 200
        assert client.get("/ui/gascalc/").status_code == 200
        assert client.get("/ui/nmr/").status_code == 200
        assert client.get("/ui/../store.py").status_code == 404
        assert client.get("/ui/%2e%2e/store.py").status_code == 404


def test_roundtrip_experience_and_note_survives_restart(tmp_path):
    path = tmp_path / "persistent.sqlite3"
    headers = {"Authorization": "Bearer " + TOKEN}
    note = {
        "event_id": "ui-note-1",
        "experiment_id": "LPP-26-050",
        "text": "Observation de test",
    }
    with TestClient(create_app(path, TOKEN), headers=headers) as client:
        assert (
            client.post("/projects", json={"id": "P", "name": "Projet"}).status_code
            == 200
        )
        assert (
            client.post(
                "/experiments",
                json={"id": "LPP-26-050", "project_id": "P", "name": "Essai"},
            ).status_code
            == 200
        )
        result = client.post("/notes", json=note)
        assert result.status_code == 200
        assert result.json()["status"] == "draft_local"
        assert result.headers["cache-control"] == "no-store"
    with TestClient(create_app(path, TOKEN), headers=headers) as client:
        assert client.get("/experiments?project_id=P").json()[0]["id"] == "LPP-26-050"
        assert client.post("/notes", json=note).status_code == 200
        events = client.get("/events?experiment_id=LPP-26-050").json()
        assert len(events) == 1
        assert events[0]["text"] == note["text"]
