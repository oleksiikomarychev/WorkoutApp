from kombu.transport.redis import Channel
from workouts_service.celery_app import celery_app


def test_celery_redis_transport_client_compatible_with_kombu() -> None:
    """Verify kombu Redis transport accepts the installed redis-py version."""
    connection = celery_app.connection()
    assert connection.transport.driver_type == "redis"

    channel = Channel.__new__(Channel)
    channel.global_keyprefix = ""
    client_cls = channel._get_client()
    assert client_cls is not None
