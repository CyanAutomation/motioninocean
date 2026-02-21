import sys
import threading
from unittest.mock import patch

import pytest


def test_load_config_discovery_defaults(monkeypatch, workspace_root):
    original_path = sys.path.copy()
    sys.path.insert(0, str(workspace_root))  # Add parent dir to sys.path
    try:
        from pi_camera_in_docker import main

        monkeypatch.delenv("DISCOVERY_ENABLED", raising=False)
        monkeypatch.delenv("DISCOVERY_MANAGEMENT_URL", raising=False)
        monkeypatch.delenv("DISCOVERY_TOKEN", raising=False)
        monkeypatch.delenv("DISCOVERY_INTERVAL_SECONDS", raising=False)
        monkeypatch.delenv("DISCOVERY_WEBCAM_ID", raising=False)
        monkeypatch.delenv("BASE_URL", raising=False)

        cfg = main._load_config()

        assert cfg["discovery_enabled"] is False
        assert cfg["discovery_management_url"] == "http://127.0.0.1:8001"
        assert cfg["discovery_token"] == ""
        assert cfg["discovery_interval_seconds"] == 30.0
        assert cfg["discovery_webcam_id"] == ""
        assert cfg["base_url"].startswith("http://")
    finally:
        sys.path = original_path


def test_load_config_discovery_overrides(monkeypatch, workspace_root):
    original_path = sys.path.copy()
    sys.path.insert(0, str(workspace_root))  # Add parent dir to sys.path
    try:
        from pi_camera_in_docker import main

        monkeypatch.setenv("MIO_DISCOVERY_ENABLED", "true")
        monkeypatch.setenv("MIO_DISCOVERY_MANAGEMENT_URL", "http://192.168.1.100:8001")
        monkeypatch.setenv("MIO_DISCOVERY_TOKEN", "top-secret")
        monkeypatch.setenv("MIO_DISCOVERY_INTERVAL_SECONDS", "12")
        monkeypatch.setenv("MIO_DISCOVERY_WEBCAM_ID", "node-override")
        monkeypatch.setenv("MIO_BASE_URL", "http://camera.local:8000")

        cfg = main._load_config()

        assert cfg["discovery_enabled"] is True
        assert cfg["discovery_management_url"] == "http://192.168.1.100:8001"
        assert cfg["discovery_token"] == "top-secret"
        assert cfg["discovery_interval_seconds"] == 12.0
        assert cfg["discovery_webcam_id"] == "node-override"
        assert cfg["base_url"] == "http://camera.local:8000"
    finally:
        sys.path = original_path


def test_build_discovery_payload_uses_override_node_id():
    from discovery import build_discovery_payload

    payload = build_discovery_payload(
        {
            "discovery_webcam_id": "node-explicit",
            "discovery_base_url": "http://camera.local:8000",
        }
    )

    assert payload["webcam_id"] == "node-explicit"
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
        webcam_id="node-1",
        payload={"webcam_id": "node-1"},
        shutdown_event=shutdown_event,
    )

    announcer.stop()

    assert shutdown_event.is_set()


def test_build_discovery_payload_requires_base_url():
    from discovery import build_discovery_payload

    with pytest.raises(ValueError, match="discovery_base_url is required"):
        build_discovery_payload({"discovery_webcam_id": "node-explicit"})


def test_discovery_announcer_log_url_redacts_query_and_credentials():
    from discovery import DiscoveryAnnouncer

    shutdown_event = threading.Event()
    announcer = DiscoveryAnnouncer(
        management_url="http://user:pass@example.local:8001?token=secret",
        token="token",
        interval_seconds=30,
        webcam_id="node-1",
        payload={"webcam_id": "node-1"},
        shutdown_event=shutdown_event,
    )

    assert announcer.management_url_log == "http://example.local:8001/api/discovery/announce"


@pytest.mark.parametrize(
    ("management_url", "expected_host", "expected_port"),
    [
        ("http://192.168.1.10:8001", "192.168.1.10", 8001),
        ("http://management.local:8001", "management.local", 8001),
        ("http://[2001:db8::1]:8001", "2001:db8::1", 8001),
    ],
)
def test_safe_management_url_handles_host_formats(management_url, expected_host, expected_port):
    from urllib.parse import urlsplit

    from pi_camera_in_docker.discovery import _safe_management_url

    safe_url = _safe_management_url(management_url)
    parsed = urlsplit(safe_url)

    assert safe_url.endswith("/api/discovery/announce")
    assert parsed.hostname == expected_host
    assert parsed.port == expected_port


def test_discovery_announcer_start_is_thread_safe_and_idempotent():
    from discovery import DiscoveryAnnouncer

    shutdown_event = threading.Event()
    announcer = DiscoveryAnnouncer(
        management_url="http://127.0.0.1:8001",
        token="token",
        interval_seconds=30,
        webcam_id="node-1",
        payload={"webcam_id": "node-1"},
        shutdown_event=shutdown_event,
    )

    started_threads = []
    barrier = threading.Barrier(8)

    def start_from_worker() -> None:
        barrier.wait()
        announcer.start()

    with patch.object(announcer, "_run_loop", side_effect=shutdown_event.wait):
        for _ in range(8):
            worker = threading.Thread(target=start_from_worker)
            started_threads.append(worker)
            worker.start()

        for worker in started_threads:
            worker.join(timeout=2.0)

        thread_ref = announcer._thread
        assert thread_ref is not None
        assert thread_ref.is_alive()
        assert thread_ref.name == "discovery-announcer"

        announcer.start()
        assert announcer._thread is thread_ref

        announcer.stop(timeout_seconds=1.0)
        announcer.stop(timeout_seconds=1.0)

        assert shutdown_event.is_set()
        assert not thread_ref.is_alive()


def test_create_webcam_app_initializes_discovery_with_webcam_id(full_config, monkeypatch):
    from pi_camera_in_docker import main

    captured = {}

    class FakeAnnouncer:
        def __init__(
            self,
            management_url,
            token,
            interval_seconds,
            webcam_id,
            payload,
            shutdown_event,
        ):
            captured["management_url"] = management_url
            captured["token"] = token
            captured["interval_seconds"] = interval_seconds
            captured["webcam_id"] = webcam_id
            captured["payload"] = payload
            captured["shutdown_event"] = shutdown_event
            captured["started"] = False

        def start(self):
            captured["started"] = True

    payload = {
        "webcam_id": "webcam-test-1",
        "base_url": "http://localhost:8000",
        "transport": "http",
        "capabilities": ["stream"],
    }

    monkeypatch.setattr(main, "DiscoveryAnnouncer", FakeAnnouncer)
    monkeypatch.setattr(main, "build_discovery_payload", lambda _cfg: payload)

    cfg = dict(full_config)
    cfg["discovery_enabled"] = True
    cfg["discovery_management_url"] = "http://management.local:8001"
    cfg["discovery_token"] = "secret-token"
    cfg["discovery_interval_seconds"] = 15.0
    cfg["base_url"] = "http://localhost:8000"
    cfg["mock_camera"] = True

    app = main.create_webcam_app(cfg)

    assert app.motion_state["discovery_announcer"] is not None
    assert captured["started"] is True
    assert captured["webcam_id"] == payload["webcam_id"]
    assert captured["payload"] == payload


def test_discovery_announcer_can_restart_after_stop(monkeypatch):
    from discovery import DiscoveryAnnouncer

    shutdown_event = threading.Event()
    announcer = DiscoveryAnnouncer(
        management_url="http://127.0.0.1:8001",
        token="token",
        interval_seconds=1,
        webcam_id="node-1",
        payload={"webcam_id": "node-1"},
        shutdown_event=shutdown_event,
    )

    announce_calls = []
    second_start_announced = threading.Event()

    def fake_announce_once() -> bool:
        announce_calls.append(True)
        if len(announce_calls) >= 2:
            second_start_announced.set()
        return True

    monkeypatch.setattr(announcer, "_announce_once", fake_announce_once)

    announcer.start()
    assert len(announce_calls) > 0

    announcer.stop(timeout_seconds=1.0)
    assert shutdown_event.is_set()

    announcer.start()
    assert not shutdown_event.is_set()
    assert second_start_announced.wait(timeout=2.0)
    assert len(announce_calls) >= 2

    announcer.stop(timeout_seconds=1.0)
