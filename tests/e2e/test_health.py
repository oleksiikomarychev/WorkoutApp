import pytest


@pytest.mark.asyncio
async def test_gateway_health(base_url, http_client):
    resp = await http_client.get(f"{base_url}/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "ok"


@pytest.mark.asyncio
async def test_upstreams_health(base_url, http_client, internal_secret_headers):
    resp = await http_client.get(
        f"{base_url}/api/v1/upstreams/health",
        headers=internal_secret_headers,
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert "services" in payload

    services = payload["services"]

    for key in ["rpe", "exercises", "user_max", "workouts", "plans", "agent", "accounts"]:
        assert key in services
        assert isinstance(services[key], dict)

        assert "ok" in services[key]
