"""Run a hermetic local demo via ASGI, with fictitious data only."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from chemlab.app import create_app


def main():
    with TemporaryDirectory() as directory:
        root = Path(directory)
        index = root / "records.jsonl"
        index.write_text(
            json.dumps(
                {
                    "source_name": "FICTITIOUS balance procedure",
                    "page_number": 1,
                    "text": "Confirm a stable mass reading before recording the observation.",
                }
            )
            + "\n"
        )
        token = "local-demo-token-not-for-production"
        client = TestClient(
            create_app(root / "demo.sqlite3", token, index),
            headers={"Authorization": "Bearer " + token},
        )
        requests = [
            (
                "POST",
                "/devices",
                {
                    "id": "balance-demo",
                    "name": "Simulated balance",
                    "location": "Demo bench",
                    "capability": "mass.read_stable",
                },
            ),
            (
                "POST",
                "/observations",
                {
                    "event_id": "reading-1",
                    "device_id": "balance-demo",
                    "experiment_id": "DEMO-001",
                    "value": 12.5,
                    "unit": "g",
                    "stable": True,
                    "observed_at": "2026-01-01T12:00:00Z",
                },
            ),
            (
                "POST",
                "/notes",
                {
                    "event_id": "note-1",
                    "experiment_id": "DEMO-001",
                    "text": "Fictitious observation: clear solution.",
                },
            ),
            (
                "POST",
                "/inventory/calculate",
                {
                    "gross_g": "1240",
                    "tare_g": "340",
                    "density_g_ml": "0.9",
                    "tare_kind": "estimated",
                },
            ),
            ("GET", "/events?experiment_id=DEMO-001", None),
            ("GET", "/literature/search?q=stable%20mass", None),
        ]
        with client:
            for method, url, payload in requests:
                response = client.request(method, url, **({"json": payload} if payload is not None else {}))
                response.raise_for_status()
                print(json.dumps({"endpoint": url, "result": response.json()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
