from fastapi.testclient import TestClient


def test_instances_crud_and_from_plan(client: TestClient):
    # Create a base plan
    plan_payload = {
        "name": "Base Plan",
        "schedule": {"day1": []},
        "duration_weeks": 4,
    }
    r = client.post("/api/v1/calendar-plans", json=plan_payload)
    assert r.status_code == 201, r.text
    plan = r.json()
    pid = plan["id"]

    # Create instance from plan
    r = client.post(f"/api/v1/calendar-plan-instances/from-plan/{pid}")
    assert r.status_code == 201, r.text
    inst = r.json()
    iid = inst["id"]
    assert inst["source_plan_id"] == pid
    assert inst["name"] == plan_payload["name"]

    # List instances
    r = client.get("/api/v1/calendar-plan-instances")
    assert r.status_code == 200
    assert any(x["id"] == iid for x in r.json())

    # Get instance
    r = client.get(f"/api/v1/calendar-plan-instances/{iid}")
    assert r.status_code == 200

    # Update instance
    r = client.put(f"/api/v1/calendar-plan-instances/{iid}", json={"name": "Edited"})
    assert r.status_code == 200
    assert r.json()["name"] == "Edited"

    # Apply stub (501)
    r = client.post(f"/api/v1/calendar-plan-instances/{iid}/apply", json={"user_max_ids": [], "compute": {}})
    assert r.status_code == 501

    # Delete instance
    r = client.delete(f"/api/v1/calendar-plan-instances/{iid}")
    assert r.status_code == 204
