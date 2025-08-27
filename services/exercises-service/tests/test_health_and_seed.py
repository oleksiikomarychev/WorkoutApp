from typing import List

from fastapi.testclient import TestClient


def test_health(client: TestClient):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_seed_exercises_present(client: TestClient):
    r = client.get("/api/v1/exercises/list")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

    names = {item["name"] for item in data}
    # Expect at least the big three
    assert {"Back Squat", "Bench Press", "Deadlift"}.issubset(names)


def test_list_filter_by_ids(client: TestClient):
    # Fetch all to learn existing IDs (portable across sqlite)
    r_all = client.get("/api/v1/exercises/list")
    assert r_all.status_code == 200
    all_items = r_all.json()
    assert len(all_items) >= 3

    ids = [str(all_items[0]["id"]), str(all_items[2]["id"])]
    r = client.get("/api/v1/exercises/list", params={"ids": ",".join(ids)})
    assert r.status_code == 200
    filtered = r.json()
    assert {item["id"] for item in filtered} == {int(ids[0]), int(ids[1])}
