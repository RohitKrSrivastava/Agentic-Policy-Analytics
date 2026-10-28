from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)

def test_api_root():
    response = client.get("/")
    assert response.status_code == 200

def test_api_status():
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"

def test_datasets_endpoint():
    response = client.get("/api/v1/datasets")
    assert response.status_code == 200
    datasets = response.json()
    assert len(datasets) >= 4
    ids = [d["id"] for d in datasets]
    assert "singstat_tech_employment" in ids
    assert "mom_labour_market" in ids
    assert "datagovsg_wages" in ids

def test_llm_health_endpoint():
    response = client.get("/api/v1/llm/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert len(data["active_providers"]) >= 3

def test_create_and_fetch_analysis():
    # Submit analysis request
    payload = {
        "query": "Analyse employment trends in the technology sector from 2020-2024",
        "provider_preference": "auto"
    }
    post_res = client.post("/api/v1/analysis", json=payload)
    assert post_res.status_code == 200
    session_data = post_res.json()
    session_id = session_data["session_id"]
    assert session_id is not None
    assert session_data["status"] in ["pending", "planning", "extracting", "analyzing", "completed"]

    # Fetch session
    get_res = client.get(f"/api/v1/analysis/{session_id}")
    assert get_res.status_code == 200
    assert get_res.json()["session_id"] == session_id

def test_list_sessions():
    res = client.get("/api/v1/analysis")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
