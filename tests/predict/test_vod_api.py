import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.routes.predict import router as predict_router


@pytest.mark.asyncio
async def test_predict_vod_models():
    app = FastAPI()
    app.include_router(predict_router)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "rho_g_cc": 1.7,
            "N": 0.02,
            "M": 25.0,
            "Q_cal_g": 1000.0,
            "OB": -10.0,
            "Q_MJ_kg": 4.2,
        }
        r = await client.post("/predict/vod", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert "models" in data and isinstance(data["models"], dict)
        assert "ml_baseline" in data["models"]
        # If inputs provided, KJ and Keshavarz should appear
        assert "kamlet_jacobs" in data["models"]
        assert "keshavarz" in data["models"]
        assert data["models"]["ml_baseline"]["VoD_km_s"] >= 0.0
