from fastapi.testclient import TestClient


def test_apply_and_list_active(client: TestClient):
    # Create base plan
    plan_payload = {
        "name": "Plan A",
        "schedule": {"day1": []},
        "duration_weeks": 2,
    }
    r = client.post("/api/v1/calendar-plans", json=plan_payload)
    assert r.status_code == 201, r.text
    plan_id = r.json()["id"]

    # Apply plan with user_max_ids
    apply_payload = {
        "user_max_ids": [1, 2, 3],
        "compute": {"generate_workouts": False},
    }
    r = client.post(f"/api/v1/applied-calendar-plans/apply/{plan_id}", json=apply_payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["calendar_plan_id"] == plan_id
    assert body["is_active"] is True
    assert body["user_max_ids"] == [1, 2, 3]

    # List user applied plans
    r = client.get("/api/v1/applied-calendar-plans/user")
    assert r.status_code == 200
    lst = r.json()
    assert len(lst) >= 1

    # Get active
    r = client.get("/api/v1/applied-calendar-plans/active")
    assert r.status_code == 200
    active = r.json()
    assert active is not None
    assert active["calendar_plan_id"] == plan_id
