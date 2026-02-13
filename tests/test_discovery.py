import pytest
import threading


def test_load_config_discovery_defaults(monkeypatch):
    import main

    monkeypatch.delenv("DISCOVERY_ENABLED", raising=False)
    monkeypatch.delenv("DISCOVERY_MANAGEMENT_URL", raising=False)
    monkeypatch.delenv("DISCOVERY_TOKEN", raising=False)
    monkeypatch.delenv("DISCOVERY_INTERVAL_SECONDS", raising=False)
    monkeypatch.delenv("DISCOVERY_NODE_ID", raising=False)
    monkeypatch.delenv("BASE_URL", raising=False)

    cfg = main._load_config()

    assert cfg["discovery_enabled"] is False
    assert cfg["discovery_management_url"] == "http://127.0.0.1:8001"
    assert cfg["discovery_token"] == ""
    assert cfg["discovery_interval_seconds"] == 30.0
    assert cfg["discovery_node_id"] == ""
    assert cfg["base_url"].startswith("http://")


def test_load_config_discovery_overrides(monkeypatch):
    import main

    monkeypatch.setenv("DISCOVERY_ENABLED", "true")
    monkeypatch.setenv("DISCOVERY_MANAGEMENT_URL", "http://192.168.1.100:8001")
    monkeypatch.setenv("DISCOVERY_TOKEN", "top-secret")
    monkeypatch.setenv("DISCOVERY_INTERVAL_SECONDS", "12")
    monkeypatch.setenv("DISCOVERY_NODE_ID", "node-override")
    monkeypatch.setenv("BASE_URL", "http://camera.local:8000")

    cfg = main._load_config()

    assert cfg["discovery_enabled"] is True
    assert cfg["discovery_management_url"] == "http://192.168.1.100:8001"
    assert cfg["discovery_token"] == "top-secret"
    assert cfg["discovery_interval_seconds"] == 12.0
    assert cfg["discovery_node_id"] == "node-override"
    assert cfg["base_url"] == "http://camera.local:8000"


def test_build_discovery_payload_uses_override_node_id():
    from discovery import build_discovery_payload

    payload = build_discovery_payload(
        {
            "discovery_node_id": "node-explicit",
            "discovery_base_url": "http://camera.local:8000",
        }
    )

    assert payload["node_id"] == "node-explicit"
    assert payload["base_url"] == "http://camera.local:8000"
    assert payload["transport"] == "http"
    assert "stream" in payload["capabilities"]
    assert "snapshot" in payload["capabilities"]


def test_discovery_announcer_stop_sets_shutdown_event():
    from discovery import DiscoveryAnnouncer

    shutdown_event = threading.Event()
    announcer = DiscoveryAnnouncer(
        management_url="http://127.0.0.1:8001",
        token="token",
        interval_seconds=30,
        node_id="node-1",
        payload={"node_id": "node-1"},
        shutdown_event=shutdown_event,
    )

    announcer.stop()

    assert shutdown_event.is_set()


def test_build_discovery_payload_requires_base_url():
    from discovery import build_discovery_payload

    with pytest.raises(ValueError, match="discovery_base_url is required"):
        build_discovery_payload({"discovery_node_id": "node-explicit"})


def test_discovery_announcer_log_url_redacts_query_and_credentials():
    from discovery import DiscoveryAnnouncer

    shutdown_event = threading.Event()
    announcer = DiscoveryAnnouncer(
        management_url="http://user:pass@example.local:8001?token=secret",
        token="token",
        interval_seconds=30,
        node_id="node-1",
        payload={"node_id": "node-1"},
        shutdown_event=shutdown_event,
    )

    assert announcer.management_url_log == "http://example.local:8001/api/discovery/announce"
