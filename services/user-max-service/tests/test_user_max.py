from fastapi.testclient import TestClient


def test_health(client: TestClient):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_user_max_crud_flow(client: TestClient):
    # Initially empty
    r_list = client.get("/api/v1/user-maxes/")
    assert r_list.status_code == 200
    assert r_list.json() == []

    # Create
    payload = {"exercise_id": 1, "max_weight": 150, "rep_max": 1}
    r_create = client.post("/api/v1/user-maxes/", json=payload)
    assert r_create.status_code == 201, r_create.text
    created = r_create.json()
    assert created["exercise_id"] == 1
    assert created["max_weight"] == 150
    assert created["rep_max"] == 1
    uid = created["id"]

    # Read by id
    r_get = client.get(f"/api/v1/user-maxes/{uid}")
    assert r_get.status_code == 200
    assert r_get.json()["id"] == uid

    # List by exercise
    r_by_ex = client.get("/api/v1/user-maxes/by_exercise/1")
    assert r_by_ex.status_code == 200
    data = r_by_ex.json()
    assert len(data) == 1 and data[0]["id"] == uid

    # Update by id
    upd = {"exercise_id": 1, "max_weight": 155, "rep_max": 2}
    r_upd = client.put(f"/api/v1/user-maxes/{uid}", json=upd)
    assert r_upd.status_code == 200
    after = r_upd.json()
    assert after["max_weight"] == 155 and after["rep_max"] == 2

    # Delete
    r_del = client.delete(f"/api/v1/user-maxes/{uid}")
    assert r_del.status_code == 204

    # Ensure 404 after delete
    r_404 = client.get(f"/api/v1/user-maxes/{uid}")
    assert r_404.status_code == 404
