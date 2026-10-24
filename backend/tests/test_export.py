import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_export_endpoints_markdown_and_json_and_pdf():
    # 1. Run an analysis session first
    post_res = client.post("/api/v1/analysis", json={
        "query": "Analyse employment trends in the technology sector from 2020-2024",
        "provider_preference": "local_fallback"
    })
    session_id = post_res.json()["session_id"]

    # Allow background execution
    import time
    time.sleep(2.0)

    # 2. Test Markdown Export
    md_res = client.get(f"/api/v1/export/{session_id}/markdown")
    assert md_res.status_code == 200
    assert "Executive Summary" in md_res.text
    assert "SINGSTAT-M015661" in md_res.text

    # 3. Test JSON Bundle Export
    json_res = client.get(f"/api/v1/export/{session_id}/json")
    assert json_res.status_code == 200
    json_data = json_res.json()
    assert json_data["session_id"] == session_id
    assert "report" in json_data
    assert "charts" in json_data

    # 4. Test PDF Export
    pdf_res = client.get(f"/api/v1/export/{session_id}/pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 1000 # Valid binary PDF

def test_dataset_previews():
    for ds_id in ["singstat_tech_employment", "mom_labour_market", "datagovsg_wages", "mom_turnover_excel", "internal_policy_db"]:
        res = client.get(f"/api/v1/datasets/{ds_id}/preview")
        assert res.status_code == 200
