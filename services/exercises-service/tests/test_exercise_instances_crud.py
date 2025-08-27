from typing import List, Dict, Any

from fastapi.testclient import TestClient


def _pick_exercise_id(client: TestClient) -> int:
    r = client.get("/api/v1/exercises/list")
    r.raise_for_status()
    items = r.json()
    assert isinstance(items, list) and items, "Seed exercises must be present"
    return int(items[0]["id"])  # pick first available


def test_exercise_instance_crud_flow(client: TestClient):
    exercise_id = _pick_exercise_id(client)

    # Create
    payload = {
        "exercise_list_id": exercise_id,
        "sets": [
            {"weight": 100, "reps": 5, "rpe": 8},
            {"weight": 105, "reps": 3, "rpe": 9},
        ],
        "notes": "initial note",
        "order": 1,
    }
    r_create = client.post("/api/v1/exercises/workouts/1/instances", json=payload)
    assert r_create.status_code == 201, r_create.text
    created = r_create.json()
    instance_id = created["id"]
    assert created["exercise_list_id"] == exercise_id
    assert created["workout_id"] == 1
    assert isinstance(created["sets"], list) and len(created["sets"]) == 2
    # ensure set ids and normalized keys exist
    set_ids = [s.get("id") for s in created["sets"]]
    assert all(isinstance(sid, int) and sid > 0 for sid in set_ids)
    assert all("reps" in s and "rpe" in s for s in created["sets"])  # normalized for frontend

    # Read
    r_get = client.get(f"/api/v1/exercises/instances/{instance_id}")
    assert r_get.status_code == 200
    got = r_get.json()
    assert got["id"] == instance_id
    assert len(got["sets"]) == 2

    # Update whole instance (change notes/order and adjust weights)
    set1_id = got["sets"][0]["id"]
    set2_id = got["sets"][1]["id"]
    upd_payload = {
        "exercise_list_id": exercise_id,
        "sets": [
            {"id": set1_id, "weight": 102.5, "reps": 5, "rpe": 7.5},
            {"id": set2_id, "weight": 107.5, "reps": 3, "rpe": 9},
        ],
        "notes": "updated note",
        "order": 2,
    }
    r_upd = client.put(f"/api/v1/exercises/instances/{instance_id}", json=upd_payload)
    assert r_upd.status_code == 200, r_upd.text
    after_upd = r_upd.json()
    assert after_upd["notes"] == "updated note"
    assert after_upd["order"] == 2
    # weights should reflect updates
    weights = [s.get("weight") for s in after_upd["sets"]]
    assert 102.5 in weights and 107.5 in weights

    # Update single set via dedicated endpoint (change reps/rpe)
    r_set_upd = client.put(
        f"/api/v1/exercises/instances/{instance_id}/sets/{set1_id}",
        json={"reps": 6, "rpe": 8.5},
    )
    assert r_set_upd.status_code == 200, r_set_upd.text
    after_set_upd = r_set_upd.json()
    s1 = next(s for s in after_set_upd["sets"] if s["id"] == set1_id)
    assert s1["reps"] == 6
    assert float(s1["rpe"]) == 8.5

    # Delete one set
    r_del_set = client.delete(f"/api/v1/exercises/instances/{instance_id}/sets/{set2_id}")
    assert r_del_set.status_code == 204
    r_after_del = client.get(f"/api/v1/exercises/instances/{instance_id}")
    assert r_after_del.status_code == 200
    sets_now = r_after_del.json()["sets"]
    assert len(sets_now) == 1 and sets_now[0]["id"] == set1_id

    # Delete instance
    r_del_inst = client.delete(f"/api/v1/exercises/instances/{instance_id}")
    assert r_del_inst.status_code == 204
    r_get_deleted = client.get(f"/api/v1/exercises/instances/{instance_id}")
    assert r_get_deleted.status_code == 404
