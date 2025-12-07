import pytest


@pytest.mark.asyncio
async def test_applied_plans_apply_and_active(base_url, http_client, internal_secret_headers):
    user_id = "e2e-plans-user"
    headers = {**internal_secret_headers, "X-User-Id": user_id, "Content-Type": "application/json"}

    plan_payload = {
        "name": "E2E Calendar Plan",
        "duration_weeks": 4,
        "mesocycles": [
            {
                "name": "Mesocycle 1",
                "order_index": 0,
                "duration_weeks": 4,
                "microcycles": [
                    {
                        "name": "Microcycle 1",
                        "days_count": 7,
                        "order_index": 0,
                        "normalization_value": None,
                        "normalization_unit": None,
                        "plan_workouts": [],
                    }
                ],
            }
        ],
    }

    resp_plan = await http_client.post(
        f"{base_url}/api/v1/plans/calendar-plans/",
        headers=headers,
        json=plan_payload,
    )
    assert resp_plan.status_code in (200, 201)
    plan = resp_plan.json()
    plan_id = plan.get("id")
    assert isinstance(plan_id, int)

    compute = {
        "compute_weights": False,
        "rounding_step": 2.5,
        "rounding_mode": "nearest",
        "generate_workouts": False,
    }

    resp_apply = await http_client.post(
        f"{base_url}/api/v1/plans/applied-plans/apply/{plan_id}",
        headers=headers,
        params={"user_max_ids": "1"},
        json=compute,
    )
    assert resp_apply.status_code == 200
    applied = resp_apply.json()
    applied_plan_id = applied.get("id")
    assert isinstance(applied_plan_id, int)

    resp_active = await http_client.get(
        f"{base_url}/api/v1/plans/applied-plans/active",
        headers=headers,
    )
    assert resp_active.status_code == 200
    active = resp_active.json()
    assert active is not None
    assert active.get("id") == applied_plan_id
    assert active.get("calendar_plan_id") == plan_id
    assert active.get("is_active") is True
    assert active.get("status") == "active"

    resp_active_workouts = await http_client.get(
        f"{base_url}/api/v1/plans/applied-plans/active/workouts",
        headers=headers,
    )
    assert resp_active_workouts.status_code == 200
    workouts = resp_active_workouts.json()
    assert isinstance(workouts, list)


@pytest.mark.asyncio
async def test_applied_plans_apply_async_and_task_status(base_url, http_client, internal_secret_headers):
    user_id = "e2e-plans-async"
    headers = {**internal_secret_headers, "X-User-Id": user_id, "Content-Type": "application/json"}

    plan_payload = {
        "name": "E2E Calendar Plan Async",
        "duration_weeks": 4,
        "mesocycles": [
            {
                "name": "Mesocycle 1",
                "order_index": 0,
                "duration_weeks": 4,
                "microcycles": [
                    {
                        "name": "Microcycle 1",
                        "days_count": 7,
                        "order_index": 0,
                        "normalization_value": None,
                        "normalization_unit": None,
                        "plan_workouts": [],
                    }
                ],
            }
        ],
    }

    resp_plan = await http_client.post(
        f"{base_url}/api/v1/plans/calendar-plans/",
        headers=headers,
        json=plan_payload,
    )
    assert resp_plan.status_code in (200, 201)
    plan = resp_plan.json()
    plan_id = plan.get("id")
    assert isinstance(plan_id, int)

    compute = {
        "compute_weights": False,
        "rounding_step": 2.5,
        "rounding_mode": "nearest",
        "generate_workouts": False,
    }

    resp_async = await http_client.post(
        f"{base_url}/api/v1/plans/applied-plans/apply-async/{plan_id}",
        headers=headers,
        params={"user_max_ids": "1"},
        json=compute,
    )
    assert resp_async.status_code == 200
    data = resp_async.json()
    task_id = data.get("task_id")
    assert isinstance(task_id, str)
    assert task_id

    resp_status = await http_client.get(
        f"{base_url}/api/v1/plans/applied-plans/tasks/{task_id}",
        headers=headers,
    )
    assert resp_status.status_code == 200
    status_data = resp_status.json()
    assert status_data.get("task_id") == task_id
    status_val = status_data.get("status")
    assert isinstance(status_val, str)


@pytest.mark.asyncio
async def test_workouts_next_in_plan(base_url, http_client, internal_secret_headers):
    user_id = "e2e-workouts-next"
    headers = {**internal_secret_headers, "X-User-Id": user_id, "Content-Type": "application/json"}

    applied_plan_id = 12345

    workout1_payload = {
        "name": "E2E Workout 1",
        "applied_plan_id": applied_plan_id,
        "plan_order_index": 0,
        "status": "planned",
    }
    resp1 = await http_client.post(
        f"{base_url}/api/v1/workouts/",
        headers=headers,
        json=workout1_payload,
    )
    assert resp1.status_code in (200, 201)
    w1 = resp1.json()
    w1_id = w1.get("id")
    assert isinstance(w1_id, int)

    workout2_payload = {
        "name": "E2E Workout 2",
        "applied_plan_id": applied_plan_id,
        "plan_order_index": 1,
        "status": "planned",
    }
    resp2 = await http_client.post(
        f"{base_url}/api/v1/workouts/",
        headers=headers,
        json=workout2_payload,
    )
    assert resp2.status_code in (200, 201)
    w2 = resp2.json()
    w2_id = w2.get("id")
    assert isinstance(w2_id, int)

    resp_next = await http_client.get(
        f"{base_url}/api/v1/workouts/{w1_id}/next",
        headers=headers,
    )
    assert resp_next.status_code == 200
    next_w = resp_next.json()
    assert next_w.get("id") == w2_id
    assert next_w.get("applied_plan_id") == applied_plan_id

    resp_no_next = await http_client.get(
        f"{base_url}/api/v1/workouts/{w2_id}/next",
        headers=headers,
    )
    assert resp_no_next.status_code == 404
