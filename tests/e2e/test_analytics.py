import os
from datetime import datetime, timedelta

import pytest

WORKOUTS_BASE_URL = os.getenv("WORKOUTS_BASE_URL", "http://localhost:8004").rstrip("/")


async def _cleanup_workouts_user(http_client, user_id: str) -> None:
    try:
        await http_client.post(
            f"{WORKOUTS_BASE_URL}/workouts/debug/cleanup-user",
            json={"user_id": user_id},
        )
    except Exception:
        pass


def _user_headers(internal_secret_headers: dict[str, str], user_id: str) -> dict[str, str]:
    return {**internal_secret_headers, "X-User-Id": user_id}


def _json_headers(internal_secret_headers: dict[str, str], user_id: str) -> dict[str, str]:
    return {**_user_headers(internal_secret_headers, user_id), "Content-Type": "application/json"}


async def _create_workout(base_url: str, http_client, headers: dict[str, str], name: str, **extra) -> dict:
    payload = {"name": name}
    payload.update(extra)
    resp = await http_client.post(f"{base_url}/api/v1/workouts/", headers=headers, json=payload)
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert isinstance(data.get("id"), int)
    return data


async def _create_exercise_definition(
    base_url: str, http_client, headers: dict[str, str], name: str, equipment: str
) -> dict:
    resp = await http_client.post(
        f"{base_url}/api/v1/exercises/definitions/", headers=headers, json={"name": name, "equipment": equipment}
    )
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert isinstance(data.get("id"), int)
    return data


async def _create_exercise_instance(
    base_url: str,
    http_client,
    headers: dict[str, str],
    workout_id: int,
    exercise_list_id: int,
    sets: list[dict],
) -> dict:
    resp = await http_client.post(
        f"{base_url}/api/v1/exercises/instances/workouts/{workout_id}/instances",
        headers=headers,
        json={"exercise_list_id": exercise_list_id, "sets": sets},
    )
    assert resp.status_code in (200, 201)
    return resp.json()


@pytest.mark.asyncio
async def test_profile_aggregates_empty_user(base_url, http_client, internal_secret_headers):
    user_id = "e2e-aggregates-user"
    await _cleanup_workouts_user(http_client, user_id)
    headers = _user_headers(internal_secret_headers, user_id)

    resp = await http_client.get(
        f"{base_url}/api/v1/profile/aggregates",
        headers=headers,
        params={"weeks": 4, "limit": 10},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("weeks") == 4
    assert data.get("total_workouts") == 0
    assert data.get("total_volume") == 0.0
    assert data.get("active_days") == 0
    assert data.get("completed_sessions") == []
    assert data.get("activity_map") == {}


@pytest.mark.asyncio
async def test_workout_metrics_empty_user(base_url, http_client, internal_secret_headers):
    user_id = "e2e-metrics-user"
    await _cleanup_workouts_user(http_client, user_id)
    headers = _user_headers(internal_secret_headers, user_id)

    resp = await http_client.get(
        f"{base_url}/api/v1/workout-metrics",
        headers=headers,
        params={"metric_x": "volume", "metric_y": "effort"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("requested") == {"x": "volume", "y": "effort"}
    assert isinstance(data.get("items"), list)
    assert data.get("items") == []
    assert isinstance(data.get("one_rm"), list)
    assert set(data.get("allowed_metrics", [])) >= {"volume", "effort", "reps", "kpsh", "1rm"}


@pytest.mark.asyncio
async def test_workout_metrics_invalid_metric(base_url, http_client, internal_secret_headers):
    user_id = "e2e-metrics-invalid"
    await _cleanup_workouts_user(http_client, user_id)
    headers = _user_headers(internal_secret_headers, user_id)

    resp = await http_client.get(
        f"{base_url}/api/v1/workout-metrics",
        headers=headers,
        params={"metric_x": "invalid", "metric_y": "volume"},
    )

    assert resp.status_code == 400
    data = resp.json()
    detail = data.get("detail", "")
    assert "metric_x and metric_y must be in" in detail


@pytest.mark.asyncio
async def test_workout_metrics_date_filter(base_url, http_client, internal_secret_headers):
    user_id = "e2e-metrics-dates"
    await _cleanup_workouts_user(http_client, user_id)
    headers = _json_headers(internal_secret_headers, user_id)

    now = datetime.utcnow()
    older_date = (now - timedelta(days=60)).isoformat()
    newer_date = (now - timedelta(days=2)).isoformat()

    w_old = await _create_workout(
        base_url,
        http_client,
        headers,
        name="E2E Metrics Old",
        status="planned",
        scheduled_for=older_date,
    )
    w_old_id = w_old.get("id")

    w_new = await _create_workout(
        base_url,
        http_client,
        headers,
        name="E2E Metrics New",
        status="planned",
        scheduled_for=newer_date,
    )
    w_new_id = w_new.get("id")

    date_from = (now - timedelta(days=7)).isoformat()
    date_to = now.isoformat()

    resp_metrics = await http_client.get(
        f"{base_url}/api/v1/workout-metrics",
        headers=headers,
        params={
            "metric_x": "volume",
            "metric_y": "effort",
            "date_from": date_from,
            "date_to": date_to,
        },
    )
    assert resp_metrics.status_code == 200
    data = resp_metrics.json()
    items = data.get("items", [])
    workout_ids = {item.get("workout_id") for item in items}

    assert w_new_id in workout_ids
    assert w_old_id not in workout_ids


@pytest.mark.asyncio
async def test_profile_aggregates_limit(base_url, http_client, internal_secret_headers):
    user_id = "e2e-aggregates-limit"
    await _cleanup_workouts_user(http_client, user_id)
    headers_json = _json_headers(internal_secret_headers, user_id)

    workout_ids = []
    for idx in range(3):
        w = await _create_workout(
            base_url,
            http_client,
            headers_json,
            name=f"E2E Aggregates Workout {idx}",
            status="planned",
        )
        wid = w.get("id")
        workout_ids.append(wid)

        resp_start = await http_client.post(
            f"{base_url}/api/v1/workouts/{wid}/start",
            headers=headers_json,
        )
        assert resp_start.status_code in (200, 201)

        resp_finish = await http_client.post(
            f"{base_url}/api/v1/workouts/{wid}/finish",
            headers=headers_json,
        )
        assert resp_finish.status_code in (200, 201)

    resp_agg = await http_client.get(
        f"{base_url}/api/v1/profile/aggregates",
        headers=_user_headers(internal_secret_headers, user_id),
        params={"weeks": 52, "limit": 2},
    )

    assert resp_agg.status_code == 200
    data = resp_agg.json()

    assert data.get("total_workouts") >= 3
    completed_sessions = data.get("completed_sessions", [])
    assert len(completed_sessions) == 2
    returned_workout_ids = {s.get("workout_id") for s in completed_sessions}

    assert len(returned_workout_ids) == 2
    assert any(wid not in returned_workout_ids for wid in workout_ids)


@pytest.mark.asyncio
async def test_profile_aggregates_non_empty_activity_and_volume(base_url, http_client, internal_secret_headers):
    user_id = "e2e-aggregates-non-empty"
    await _cleanup_workouts_user(http_client, user_id)
    headers_json = _json_headers(internal_secret_headers, user_id)

    ex = await _create_exercise_definition(
        base_url, http_client, headers_json, name="E2E Aggregates Exercise", equipment="barbell"
    )
    ex_id = ex.get("id")

    w = await _create_workout(
        base_url,
        http_client,
        headers_json,
        name="E2E Aggregates Workout",
        status="planned",
    )
    wid = w.get("id")

    await _create_exercise_instance(
        base_url,
        http_client,
        headers_json,
        workout_id=wid,
        exercise_list_id=ex_id,
        sets=[{"weight": 100.0, "volume": 5}],
    )

    resp_start = await http_client.post(
        f"{base_url}/api/v1/workouts/{wid}/start",
        headers=headers_json,
    )
    assert resp_start.status_code in (200, 201)

    resp_finish = await http_client.post(
        f"{base_url}/api/v1/workouts/{wid}/finish",
        headers=headers_json,
    )
    assert resp_finish.status_code in (200, 201)

    resp_agg = await http_client.get(
        f"{base_url}/api/v1/profile/aggregates",
        headers=_user_headers(internal_secret_headers, user_id),
        params={"weeks": 4, "limit": 10},
    )

    assert resp_agg.status_code == 200
    data = resp_agg.json()

    assert data.get("total_workouts") >= 1
    assert data.get("active_days") >= 1

    activity_map = data.get("activity_map", {})
    assert isinstance(activity_map, dict)
    assert activity_map

    volumes = []
    session_counts_sum = 0
    for day, payload in activity_map.items():
        vol = float(payload.get("volume", 0.0))
        cnt = int(payload.get("session_count", 0))
        assert cnt >= 0
        assert vol >= 0.0
        volumes.append(vol)
        session_counts_sum += cnt

    assert any(v > 0.0 for v in volumes)
    assert session_counts_sum <= data.get("total_workouts")

    max_day_volume = float(data.get("max_day_volume", 0.0))
    assert max_day_volume == pytest.approx(max(volumes), rel=1e-6)


@pytest.mark.asyncio
async def test_profile_aggregates_weeks_window_vs_all_sessions(base_url, http_client, internal_secret_headers):
    user_id = "e2e-aggregates-weeks"
    await _cleanup_workouts_user(http_client, user_id)
    headers_json = _json_headers(internal_secret_headers, user_id)

    ex = await _create_exercise_definition(
        base_url, http_client, headers_json, name="E2E Aggregates Old/New Exercise", equipment="barbell"
    )
    ex_id = ex.get("id")

    now = datetime.utcnow()
    old_start = now - timedelta(days=120)
    new_start = now - timedelta(days=1)

    w_old = await _create_workout(
        base_url,
        http_client,
        headers_json,
        name="E2E Aggregates Old",
        status="planned",
    )
    wid_old = w_old.get("id")

    await _create_exercise_instance(
        base_url,
        http_client,
        headers_json,
        workout_id=wid_old,
        exercise_list_id=ex_id,
        sets=[{"weight": 50.0, "volume": 2}],
    )

    resp_start_old = await http_client.post(
        f"{base_url}/api/v1/workouts/{wid_old}/start",
        headers=headers_json,
        json={"started_at": old_start.isoformat()},
    )
    assert resp_start_old.status_code in (200, 201)

    resp_finish_old = await http_client.post(
        f"{base_url}/api/v1/workouts/{wid_old}/finish",
        headers=headers_json,
    )
    assert resp_finish_old.status_code in (200, 201)

    w_new = await _create_workout(
        base_url,
        http_client,
        headers_json,
        name="E2E Aggregates New",
        status="planned",
    )
    wid_new = w_new.get("id")

    await _create_exercise_instance(
        base_url,
        http_client,
        headers_json,
        workout_id=wid_new,
        exercise_list_id=ex_id,
        sets=[{"weight": 100.0, "volume": 3}],
    )

    resp_start_new = await http_client.post(
        f"{base_url}/api/v1/workouts/{wid_new}/start",
        headers=headers_json,
        json={"started_at": new_start.isoformat()},
    )
    assert resp_start_new.status_code in (200, 201)

    resp_finish_new = await http_client.post(
        f"{base_url}/api/v1/workouts/{wid_new}/finish",
        headers=headers_json,
    )
    assert resp_finish_new.status_code in (200, 201)

    resp_agg = await http_client.get(
        f"{base_url}/api/v1/profile/aggregates",
        headers=_user_headers(internal_secret_headers, user_id),
        params={"weeks": 4, "limit": 10},
    )

    assert resp_agg.status_code == 200
    data = resp_agg.json()

    assert data.get("total_workouts") == 2
    assert data.get("active_days") == 2

    activity_map = data.get("activity_map", {})
    assert isinstance(activity_map, dict)
    assert activity_map

    recent_day_key = new_start.date().isoformat()
    assert recent_day_key in activity_map

    old_day_key = old_start.date().isoformat()
    assert old_day_key not in activity_map

    total_volume = float(data.get("total_volume", 0.0))
    day_vol = float(activity_map[recent_day_key]["volume"])
    max_day_volume = float(data.get("max_day_volume", 0.0))

    assert total_volume == pytest.approx(300.0, rel=1e-6)
    assert day_vol == pytest.approx(300.0, rel=1e-6)
    assert max_day_volume == pytest.approx(300.0, rel=1e-6)


@pytest.mark.asyncio
async def test_workout_metrics_kpsh_and_volume_from_instances(base_url, http_client, internal_secret_headers):
    user_id = "e2e-metrics-kpsh"
    await _cleanup_workouts_user(http_client, user_id)
    headers_json = _json_headers(internal_secret_headers, user_id)

    ex_bw = await _create_exercise_definition(
        base_url, http_client, headers_json, name="E2E Bodyweight Exercise", equipment="bodyweight"
    )
    ex_bw_id = ex_bw.get("id")

    ex_bar = await _create_exercise_definition(
        base_url, http_client, headers_json, name="E2E Barbell Exercise", equipment="barbell"
    )
    ex_bar_id = ex_bar.get("id")

    w = await _create_workout(
        base_url,
        http_client,
        headers_json,
        name="E2E Metrics Instances Workout",
        status="planned",
    )
    wid = w.get("id")

    await _create_exercise_instance(
        base_url,
        http_client,
        headers_json,
        workout_id=wid,
        exercise_list_id=ex_bw_id,
        sets=[{"weight": None, "volume": 10}],
    )

    await _create_exercise_instance(
        base_url,
        http_client,
        headers_json,
        workout_id=wid,
        exercise_list_id=ex_bar_id,
        sets=[{"weight": 100.0, "volume": 5}],
    )

    resp_metrics = await http_client.get(
        f"{base_url}/api/v1/workout-metrics",
        headers=_user_headers(internal_secret_headers, user_id),
        params={
            "metric_x": "kpsh",
            "metric_y": "reps",
        },
    )
    assert resp_metrics.status_code == 200
    data = resp_metrics.json()
    items = data.get("items", [])
    assert len(items) >= 1

    metrics_item = next((it for it in items if it.get("workout_id") == wid), None)
    assert metrics_item is not None
    values = metrics_item.get("values", {})

    assert values.get("reps") == 15

    assert values.get("kpsh") == 5

    assert values.get("volume") == 500.0


@pytest.mark.asyncio
async def test_workout_metrics_1rm_series_from_user_max(base_url, http_client, internal_secret_headers):
    user_id = "e2e-metrics-1rm"
    await _cleanup_workouts_user(http_client, user_id)
    headers_json = _json_headers(internal_secret_headers, user_id)

    ex = await _create_exercise_definition(
        base_url, http_client, headers_json, name="E2E 1RM Exercise", equipment="barbell"
    )
    ex_id = ex.get("id")

    today = datetime.utcnow().date()
    today_str = today.isoformat()

    resp_um = await http_client.post(
        f"{base_url}/api/v1/user-max/",
        headers=headers_json,
        json={
            "exercise_id": ex_id,
            "max_weight": 100.0,
            "rep_max": 1,
            "date": today_str,
            "verified_1rm": 110.0,
        },
    )
    assert resp_um.status_code in (200, 201)

    date_from = datetime.utcnow() - timedelta(days=1)
    date_to = datetime.utcnow() + timedelta(days=1)

    resp_metrics = await http_client.get(
        f"{base_url}/api/v1/workout-metrics",
        headers=headers_json,
        params={
            "metric_x": "1rm",
            "metric_y": "volume",
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
        },
    )
    assert resp_metrics.status_code == 200
    data = resp_metrics.json()

    one_rm_series = data.get("one_rm", [])
    assert isinstance(one_rm_series, list)
    assert len(one_rm_series) >= 1

    point_today = next((p for p in one_rm_series if p.get("date") == today_str), None)
    assert point_today is not None
    assert point_today.get("value") == pytest.approx(110.0, rel=1e-2)
