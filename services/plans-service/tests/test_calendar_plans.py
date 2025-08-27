from fastapi.testclient import TestClient


def test_health(client: TestClient):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_crud_and_favorites_flow(client: TestClient):
    # Create
    payload = {
        "name": "Base Plan",
        "schedule": {"day1": []},
        "duration_weeks": 4,
    }
    r = client.post("/api/v1/calendar-plans", json=payload)
    assert r.status_code == 201, r.text
    plan = r.json()
    pid = plan["id"]

    # List
    r = client.get("/api/v1/calendar-plans")
    assert r.status_code == 200
    assert any(p["id"] == pid for p in r.json())

    # Get
    r = client.get(f"/api/v1/calendar-plans/{pid}")
    assert r.status_code == 200
    assert r.json()["name"] == "Base Plan"

    # Update
    r = client.put(f"/api/v1/calendar-plans/{pid}", json={"name": "Updated"})
    assert r.status_code == 200
    assert r.json()["name"] == "Updated"

    # Favorites add
    r = client.post(f"/api/v1/calendar-plans/{pid}/favorite")
    assert r.status_code == 201
    assert r.json()["is_favorite"] is True

    # Favorites list
    r = client.get("/api/v1/calendar-plans/favorites")
    assert r.status_code == 200
    favs = r.json()
    assert any(p["id"] == pid for p in favs)

    # Favorites remove
    r = client.delete(f"/api/v1/calendar-plans/{pid}/favorite")
    assert r.status_code == 204

    # Workouts stub
    r = client.get(f"/api/v1/calendar-plans/{pid}/workouts")
    assert r.status_code == 200
    assert r.json() == []

    # Delete
    r = client.delete(f"/api/v1/calendar-plans/{pid}")
    assert r.status_code == 204
