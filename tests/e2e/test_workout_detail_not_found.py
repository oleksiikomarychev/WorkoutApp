import pytest


@pytest.mark.asyncio
async def test_unknown_workout_detail_is_not_found(
    base_url, http_client, internal_secret_headers
):
    response = await http_client.get(
        f"{base_url}/api/v1/workouts/2147483647",
        headers={
            **internal_secret_headers,
            "X-User-Id": "e2e-workout-detail-other-account",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Workout not found"
