import pytest


@pytest.mark.asyncio
async def test_crm_create_link_and_list(base_url, http_client, internal_secret_headers):
    coach_id = "e2e-coach"
    athlete_id = "e2e-athlete"
    headers = {**internal_secret_headers, "X-User-Id": coach_id}

    payload = {
        "athlete_id": athlete_id,
        "note": "E2E link",
    }
    resp = await http_client.post(
        f"{base_url}/api/v1/crm/relationships/",
        headers={**headers, "Content-Type": "application/json"},
        json=payload,
    )
    assert resp.status_code == 200
    created = resp.json()
    link_id = created.get("id")
    assert isinstance(link_id, int)
    assert created.get("coach_id") == coach_id
    assert created.get("athlete_id") == athlete_id

    resp_list = await http_client.get(
        f"{base_url}/api/v1/crm/relationships/my/athletes",
        headers=headers,
    )
    assert resp_list.status_code == 200
    items = resp_list.json()
    assert isinstance(items, list)
    assert any(item.get("id") == link_id for item in items)


@pytest.mark.asyncio
async def test_crm_analytics_coach_summary(base_url, http_client, internal_secret_headers):
    coach_id = "e2e-coach-analytics"
    headers = {**internal_secret_headers, "X-User-Id": coach_id}

    resp = await http_client.get(
        f"{base_url}/api/v1/crm/analytics/coaches/my/summary",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("coach_id") == coach_id
    assert "weeks" in data
    assert "total_athletes" in data
    assert "avg_sessions_per_week" in data
