import json
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from chemlab.app import create_app
from chemlab.literature import Literature
from chemlab.store import Store

TOKEN = "testing-token-at-least-24-characters"


def client_for(path, **kwargs):
    return TestClient(
        create_app(path, TOKEN, **kwargs), headers={"Authorization": "Bearer " + TOKEN}
    )


@pytest.fixture
def client(tmp_path):
    with client_for(tmp_path / "pilot.sqlite3") as client:
        yield client


def device(client):
    response = client.post(
        "/devices",
        json={
            "id": "balance",
            "name": "Demo",
            "location": "Bench",
            "capability": "mass.read_stable",
        },
    )
    assert response.status_code == 200


def observation(**changes):
    return dict(
        event_id="reading-1",
        device_id="balance",
        experiment_id="DEMO-001",
        value=12.5,
        unit="g",
        stable=True,
        observed_at="2026-01-01T12:00:00Z",
        **changes
    )


def test_auth_all_routes_and_no_actuator(client):
    for method, url in [
        ("GET", "/health"),
        ("GET", "/devices"),
        ("GET", "/events"),
        ("POST", "/notes"),
        ("POST", "/observations"),
        ("POST", "/inventory/calculate"),
        ("GET", "/literature/search?q=x"),
    ]:
        assert (
            client.request(
                method, url, headers={"Authorization": "Bearer wrong"}
            ).status_code
            == 401
        )
    assert client.get("/docs").status_code == 404
    assert (
        client.post("/devices/balance/commands", json={"heat": True}).status_code == 404
    )
    assert client.get("/health").json()["mode"] == "simulation_only"


def test_config_requires_token(tmp_path, monkeypatch):
    monkeypatch.delenv("CHEMLAB_TOKEN", raising=False)
    with pytest.raises(RuntimeError):
        create_app(tmp_path / "pilot.sqlite3")


def test_restart_and_idempotency(tmp_path):
    path = tmp_path / "persistent.sqlite3"
    with client_for(path) as c:
        device(c)
        first = c.post("/observations", json=observation()).json()
        assert first["source"] == "simulated"
    with client_for(path) as c:
        assert c.post("/observations", json=observation()).json() == first
        changed = observation()
        changed["value"] = 99
        assert c.post("/observations", json=changed).status_code == 409
        assert len(c.get("/events").json()) == 1
        assert c.get("/events?experiment_id=OTHER").json() == []


@pytest.mark.parametrize(
    "change",
    [
        {"unit": "degC"},
        {"stable": False},
        {"observed_at": "2026-01-01T12:00:00"},
        {"device_id": "unknown"},
        {"source": "real"},
    ],
)
def test_invalid_measurements_not_saved(client, change):
    device(client)
    payload = observation()
    payload.update(change)
    assert client.post("/observations", json=payload).status_code in (404, 422)
    assert client.get("/events").json() == []


def test_devices_immutable_and_simulated(client):
    device(client)
    payload = {
        "id": "balance",
        "name": "Changed",
        "location": "Bench",
        "capability": "mass.read_stable",
    }
    assert client.post("/devices", json=payload).status_code == 409
    payload["adapter"] = "serial"
    assert client.post("/devices", json=payload).status_code == 422


def test_notes_remain_drafts_and_share_event_namespace(client):
    payload = {"event_id": "note-1", "experiment_id": "DEMO-001", "text": "Observation"}
    first = client.post("/notes", json=payload)
    assert first.json()["status"] == "draft_local"
    assert client.post("/notes", json=payload).json() == first.json()
    payload["text"] = "Changed"
    assert client.post("/notes", json=payload).status_code == 409


def test_concurrent_retries_are_single_event(tmp_path):
    store = Store(tmp_path / "concurrent.sqlite3")
    payload = {"event_id": "same", "experiment_id": "DEMO", "text": "Same note"}
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: store.append("note", payload), range(20)))
    assert all(result == results[0] for result in results)
    assert len(store.events()) == 1


def test_inventory_reference_and_invalid_inputs(client):
    payload = {
        "gross_g": "1240",
        "tare_g": "340",
        "density_g_ml": "0.9",
        "tare_kind": "estimated",
    }
    result = client.post("/inventory/calculate", json=payload).json()
    assert Decimal(result["net_g"]) == 900
    assert Decimal(result["volume_ml"]) == 1000
    assert result["quantity_status"] == "estimated"
    assert result["uncertainty_evaluated"] is False
    for change in (
        {"gross_g": "100"},
        {"density_g_ml": "0"},
        {"tare_g": "-1"},
        {"gross_g": "NaN"},
    ):
        assert (
            client.post(
                "/inventory/calculate", json=dict(payload, **change)
            ).status_code
            == 422
        )
    result = client.post(
        "/inventory/calculate",
        json={"gross_g": "10", "tare_g": "10", "tare_kind": "measured"},
    ).json()
    assert result["volume_ml"] is None
    assert Decimal(result["net_g"]) == 0


def test_thesis_export_bridge(tmp_path):
    path = tmp_path / "records.jsonl"
    path.write_text(
        json.dumps(
            {
                "source_name": "Demo procedure",
                "page_number": 2,
                "text": "Confirm stable mass before recording.",
                "source_path": "/private/secret.pdf",
            }
        )
        + "\n"
    )
    with client_for(tmp_path / "db.sqlite3", literature_path=path) as c:
        result = c.get("/literature/search?q=stable%20mass").json()
        assert result["method"] == "lexical_term_coverage"
        assert result["answer_generated"] is False
        assert result["results"][0]["page_number"] == 2
        assert result["results"][0]["score"] == 1
        assert "secret" not in json.dumps(result)
        assert len(result["index_sha256"]) == 64
        assert c.get("/literature/search?q=unmatched").json()["results"] == []
        assert c.get("/literature/search?q=!!!").status_code == 422


def test_literature_fails_explicitly(client, tmp_path):
    assert client.get("/literature/search?q=mass").status_code == 503
    path = tmp_path / "invalid.jsonl"
    path.write_text('{"text": "missing provenance"}\n')
    with pytest.raises(ValueError, match="source_name"):
        Literature(path)
