"""Unit tests for discovery URL validation in config validator."""

import importlib
import sys

import pytest

from pi_camera_in_docker.config_validator import ConfigValidationError, validate_discovery_config


@pytest.fixture
def valid_discovery_config() -> dict[str, object]:
    """Return a minimal valid discovery-enabled config."""
    return {
        "discovery_enabled": True,
        "discovery_management_url": "http://management-host:8001",
        "discovery_token": "token123456",
        "base_url": "http://webcam:8000",
    }


@pytest.mark.parametrize(
    "management_url",
    [
        "management-host:8001",
        "http:///path",
        "http://",
        "http://user:pass@management-host:8001",
        "http://management-host:99999",
    ],
)
def test_validate_discovery_config_rejects_invalid_management_urls(
    valid_discovery_config: dict[str, object], management_url: str
) -> None:
    """validate_discovery_config rejects malformed or unsafe management URLs."""
    config = dict(valid_discovery_config)
    config["discovery_management_url"] = management_url

    with pytest.raises(ConfigValidationError) as exc_info:
        validate_discovery_config(config)

    assert "MIO_DISCOVERY_MANAGEMENT_URL" in str(exc_info.value)
    assert exc_info.value.hint is not None
    assert "http://management-host:8001" in exc_info.value.hint


@pytest.mark.parametrize(
    "management_url",
    [
        "http://management-host:8001",
        "https://management.example.com",
        "http://192.168.1.10",
    ],
)
def test_validate_discovery_config_accepts_valid_management_urls(
    valid_discovery_config: dict[str, object], management_url: str
) -> None:
    """validate_discovery_config accepts valid management URLs with supported schemes."""
    config = dict(valid_discovery_config)
    config["discovery_management_url"] = management_url

    validate_discovery_config(config)


@pytest.mark.parametrize("config", [{}, {"discovery_enabled": False}], ids=["empty-config", "disabled"])
def test_validate_discovery_config_skips_management_url_when_discovery_disabled(
    config: dict[str, object],
) -> None:
    """validate_discovery_config allows missing management URL unless discovery is enabled."""
    validate_discovery_config(config)
