import pytest


@pytest.mark.asyncio
async def test_auth_me_with_internal_secret(base_url, http_client, internal_secret_headers):
    resp = await http_client.get(f"{base_url}/api/v1/auth/me", headers=internal_secret_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("uid") == internal_secret_headers["X-User-Id"]
    assert "email" in data
    assert "claims" in data


@pytest.mark.asyncio
async def test_profile_me_create_and_update(base_url, http_client, internal_secret_headers):
    user_id = "e2e-profile-user"
    headers = {**internal_secret_headers, "X-User-Id": user_id}

    resp = await http_client.get(f"{base_url}/api/v1/profile/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("user_id") == user_id
    assert "settings" in data

    update_payload = {
        "display_name": "E2E User",
        "bio": "E2E profile test",
        "is_public": True,
        "bodyweight_kg": 80.5,
    }
    patch_headers = {**headers, "Content-Type": "application/json"}
    resp_update = await http_client.patch(
        f"{base_url}/api/v1/profile/me",
        headers=patch_headers,
        json=update_payload,
    )
    assert resp_update.status_code == 200
    updated = resp_update.json()
    assert updated.get("display_name") == update_payload["display_name"]
    assert updated.get("bio") == update_payload["bio"]
    assert updated.get("is_public") is True
    assert updated.get("bodyweight_kg") == pytest.approx(update_payload["bodyweight_kg"])

    resp_again = await http_client.get(f"{base_url}/api/v1/profile/me", headers=headers)
    assert resp_again.status_code == 200
    again = resp_again.json()
    assert again.get("display_name") == update_payload["display_name"]
    assert again.get("bio") == update_payload["bio"]
    assert again.get("is_public") is True
    assert again.get("bodyweight_kg") == pytest.approx(update_payload["bodyweight_kg"])
