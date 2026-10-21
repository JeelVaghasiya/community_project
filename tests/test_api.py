"""Integration tests for FastAPI application endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["pilot_city"] == "Bengaluru"


def test_get_scenarios_endpoint():
    response = client.get("/scenarios")
    assert response.status_code == 200
    data = response.json()
    assert "100mmhr" in data


def test_get_hazard_scenario_layer():
    response = client.get("/risk/100mmhr")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) > 0


def test_post_and_get_observation():
    payload = {
        "lat": 12.9172,
        "lon": 77.6228,
        "camera_id": "test_cam_01",
        "rainfall_scenario": "100mmhr",
    }
    post_res = client.post("/observations", json=payload)
    assert post_res.status_code == 200
    obs = post_res.json()
    assert obs["camera_id"] == "test_cam_01"
    assert "cv_output" in obs
    assert "fusion_status" in obs
    assert "map_colour" in obs

    # Verify presence in GET /observations
    get_res = client.get("/observations")
    assert get_res.status_code == 200
    all_obs = get_res.json()
    assert any(o["camera_id"] == "test_cam_01" for o in all_obs)
