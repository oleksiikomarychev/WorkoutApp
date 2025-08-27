from fastapi.testclient import TestClient


def test_session_flow(client: TestClient):
    # Create workout
    r_create = client.post("/api/v1/workouts/", json={"name": "Session Flow"})
    assert r_create.status_code == 201, r_create.text
    wid = r_create.json()["id"]

    # Start session
    r_start = client.post(f"/api/v1/workouts/{wid}/start")
    assert r_start.status_code == 201, r_start.text
    sid = r_start.json()["id"]
    assert r_start.json()["status"] == "active"

    # Get active
    r_active = client.get(f"/api/v1/workouts/{wid}/active")
    assert r_active.status_code == 200
    assert r_active.json()["id"] == sid

    # History should include session
    r_hist = client.get(f"/api/v1/workouts/{wid}/history")
    assert r_hist.status_code == 200
    hist = r_hist.json()
    assert isinstance(hist, list) and any(s["id"] == sid for s in hist)

    # Finish session
    r_finish = client.post(f"/api/v1/sessions/{sid}/finish")
    assert r_finish.status_code == 200
    assert r_finish.json()["status"] == "finished"

    # Active should now be 404
    r_active2 = client.get(f"/api/v1/workouts/{wid}/active")
    assert r_active2.status_code == 404
