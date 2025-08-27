from fastapi.testclient import TestClient


def test_health(client: TestClient):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_workouts_crud_flow(client: TestClient):
    # List empty
    r_list = client.get("/api/v1/workouts/")
    assert r_list.status_code == 200
    assert r_list.json() == []

    # Create
    payload = {"name": "Day 1", "notes": "Legs"}
    r_create = client.post("/api/v1/workouts/", json=payload)
    assert r_create.status_code == 201, r_create.text
    created = r_create.json()
    assert created["name"] == "Day 1"
    assert created["notes"] == "Legs"
    wid = created["id"]

    # Get
    r_get = client.get(f"/api/v1/workouts/{wid}")
    assert r_get.status_code == 200
    assert r_get.json()["id"] == wid

    # Update
    upd = {"name": "Day 1 - Updated", "notes": "Legs+Core"}
    r_upd = client.put(f"/api/v1/workouts/{wid}", json=upd)
    assert r_upd.status_code == 200
    after = r_upd.json()
    assert after["name"] == "Day 1 - Updated"
    assert after["notes"] == "Legs+Core"

    # Delete
    r_del = client.delete(f"/api/v1/workouts/{wid}")
    assert r_del.status_code == 204

    # Ensure 404
    r_404 = client.get(f"/api/v1/workouts/{wid}")
    assert r_404.status_code == 404
