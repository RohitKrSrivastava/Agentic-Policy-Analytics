from locust import HttpUser, between, task


class PolicyAnalyticsUser(HttpUser):
    """
    Locust Load Test User:
    Simulates policy analysts submitting research queries via POST /api/v1/analysis,
    polling session status, fetching dataset previews, and checking system health.
    """
    wait_time = between(0.1, 0.4)

    @task(4)
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
                    # Poll status
                    self.client.get(f"/api/v1/analysis/{session_id}", name="/api/v1/analysis/[id]")
                else:
                    resp.failure("No session_id in response")
            else:
                resp.failure(f"Failed with status {resp.status_code}")

    @task(3)
    def fetch_datasets(self):
        self.client.get("/api/v1/datasets/previews", name="/api/v1/datasets/previews")

    @task(2)
    def check_health(self):
        self.client.get("/api/v1/status", name="/api/v1/status")
