"""Unit tests for messaging service configuration."""

from __future__ import annotations

import os
from unittest.mock import patch

from config import Settings


def test_settings_default_values() -> None:
    settings = Settings(_env_file=None)
    assert settings.service_name == "messaging-service"
    assert settings.typing_ttl == 5
    assert settings.presence_ttl == 90
    assert settings.ws_heartbeat_timeout == 60
    assert settings.ws_max_message_size == 65536


def test_settings_effective_database_url_fallback() -> None:
    settings = Settings(_env_file=None)

    # When no env var is set, uses default
    with patch.dict(os.environ, {}, clear=True):
        assert settings.effective_database_url == settings.database_url

    # When MESSAGING_DATABASE_URL is set
    with patch.dict(os.environ, {"MESSAGING_DATABASE_URL": "postgresql://test:5432/messaging_test"}, clear=True):
        assert settings.effective_database_url == "postgresql://test:5432/messaging_test"

    # When DATABASE_URL is set, takes precedence
    with patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql://primary:5432/primary_db",
            "MESSAGING_DATABASE_URL": "postgresql://test:5432/messaging_test",
        },
        clear=True,
    ):
        assert settings.effective_database_url == "postgresql://primary:5432/primary_db"


def test_settings_ignores_extra_env_vars() -> None:
    # Ensure extra env variables do not cause validation failures
    with patch.dict(os.environ, {"RANDOM_EXTRA_KEY_123": "some_value"}):
        settings = Settings(_env_file=None)
        assert settings.service_name == "messaging-service"
