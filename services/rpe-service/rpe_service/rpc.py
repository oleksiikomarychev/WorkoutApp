import httpx

from .config import settings


# Получает эффективный максимум пользователя из user-max-service по ID
async def get_effective_max(user_max_id: int) -> float:
    url = f"{settings.USER_MAX_SERVICE_URL}/api/v1/user-max/{user_max_id}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            # Приоритет: verified_1rm > true_1rm > max_weight
            return data.get("verified_1rm") or data.get("true_1rm") or data["max_weight"]
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Ошибка при запросе: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise RuntimeError(f"Ошибка подключения: {str(e)}") from e
