import json
import time
from locust import HttpUser, task, between
import websocket


class PolicyAnalyticsUser(HttpUser):
    """
    Locust Load Test User:
    Simulates policy analysts submitting research queries via POST /api/v1/analysis/query,
    polling session status, and connecting via WebSocket to receive live ReAct telemetry.
    """
    wait_time = between(1, 2)

    @task(3)
    def submit_and_track_analysis(self):
        payload = {
            "query": "Analyse employment trends in the technology sector from 2020-2024",
            "provider_preference": "local_fallback",
            "include_forecasting": True,
            "deep_verification": True
        }
        with self.client.post("/api/v1/analysis", json=payload, catch_response=True) as resp:
            if resp.status_code == 200:
                data = resp.json()
                session_id = data.get("session_id")
                if session_id:
                    resp.success()
                    # Poll for completion
                    for _ in range(5):
                        time.sleep(0.5)
                        poll_resp = self.client.get(f"/api/v1/analysis/{session_id}", name="/api/v1/analysis/[id]")
                        if poll_resp.status_code == 200:
                            pdata = poll_resp.json()
                            if pdata.get("status") in ["completed", "failed"]:
                                break
                else:
                    resp.failure("No session_id in response")
            else:
                resp.failure(f"Failed with status {resp.status_code}")

    @task(1)
    def fetch_datasets(self):
        self.client.get("/api/v1/datasets/previews", name="/api/v1/datasets/previews")

    @task(1)
    def test_websocket_telemetry(self):
        # Create lightweight session
        payload = {
            "query": "Singapore wage benchmarks 2020-2024",
            "provider_preference": "local_fallback"
        }
        resp = self.client.post("/api/v1/analysis", json=payload)
        if resp.status_code == 200:
            session_id = resp.json().get("session_id")
            if session_id:
                ws_url = f"ws://127.0.0.1:8000/ws/{session_id}"
                try:
                    ws = websocket.create_connection(ws_url, timeout=2.0)
                    ws.settimeout(1.0)
                    try:
                        msg = ws.recv()
                    except Exception:
                        pass
                    ws.close()
                except Exception:
                    # WebSocket probe in test environment
                    pass
