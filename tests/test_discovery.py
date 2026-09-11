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


def test_build_discovery_payload_validates_required_fields():
    """build_discovery_payload raises ValueError when required fields missing."""
    from discovery import build_discovery_payload

    # Test missing base_url
    with pytest.raises(ValueError, match="discovery_base_url is required"):
        build_discovery_payload({"discovery_webcam_id": "node-explicit"})

    # Could add more validation checks here


@pytest.mark.parametrize(
    ("management_url", "expected_url"),
    [
        ("http://127.0.0.1:8001", "http://127.0.0.1:8001/api/discovery/announce"),
        ("https://management.local/hub", "https://management.local/hub/api/discovery/announce"),
    ],
)
def test_discovery_announcer_direct_construction_accepts_http_urls(management_url, expected_url):
    from discovery import DiscoveryAnnouncer

    announcer = DiscoveryAnnouncer(
        management_url=management_url,
        token="token",
        interval_seconds=30,
        webcam_id="node-1",
        payload={"webcam_id": "node-1"},
        shutdown_event=threading.Event(),
    )

    assert announcer.management_url == expected_url


@pytest.mark.parametrize(
    "management_url",
    [
        "file:///tmp/management.sock",
        "ftp://management.local:8001",
        "http://user:pass@management.local:8001",
        "http:///management",
        "http://management.local:not-a-port",
        "http://management.local:99999",
    ],
)
def test_discovery_announcer_direct_construction_rejects_invalid_http_urls(management_url):
    from discovery import DiscoveryAnnouncer

    with pytest.raises(ValueError, match="management_url"):
        DiscoveryAnnouncer(
            management_url=management_url,
            token="token",
            interval_seconds=30,
            webcam_id="node-1",
            payload={"webcam_id": "node-1"},
            shutdown_event=threading.Event(),
        )


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


@pytest.mark.parametrize(
    ("management_url", "expected_url"),
    [
        (
            "http://management.local:8001",
            "http://management.local:8001/api/discovery/announce",
        ),
        (
            "http://management.local:8001/hub",
            "http://management.local:8001/hub/api/discovery/announce",
        ),
        (
            "http://management.local:8001/api/discovery/announce",
            "http://management.local:8001/api/discovery/announce",
        ),
        (
            "http://management.local:8001/hub/",
            "http://management.local:8001/hub/api/discovery/announce",
        ),
        (
            "http://management.local:8001/api/discovery/announce/",
            "http://management.local:8001/api/discovery/announce",
        ),
    ],
)
def test_safe_management_url_normalizes_and_avoids_duplicate_announce_path(
    management_url, expected_url
):
    from pi_camera_in_docker.discovery import _safe_management_url

    assert _safe_management_url(management_url) == expected_url


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

    with patch.object(announcer, "_run_loop", side_effect=announcer._stop_event.wait):
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

        assert not shutdown_event.is_set()
        assert not thread_ref.is_alive()


def test_discovery_announcer_stop_from_external_thread_joins():
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

    with patch.object(announcer, "_run_loop", side_effect=announcer._stop_event.wait):
        announcer.start()
        thread_ref = announcer._thread
        assert thread_ref is not None
        assert thread_ref.is_alive()

        join_calls = []
        original_join = thread_ref.join

        def tracked_join(*args, **kwargs):
            join_calls.append((args, kwargs))
            return original_join(*args, **kwargs)

        with patch.object(thread_ref, "join", side_effect=tracked_join):
            announcer.stop(timeout_seconds=1.0)

        assert join_calls
        assert not thread_ref.is_alive()
        assert announcer._thread is None


def test_discovery_announcer_stop_from_same_thread_skips_join_and_exits_gracefully():
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

    stop_completed = threading.Event()
    errors = []

    def run_and_stop() -> None:
        announcer._thread = threading.current_thread()
        try:
            announcer.stop(timeout_seconds=1.0)
        except Exception as exc:  # pragma: no cover - asserts below verify none raised
            errors.append(exc)
        finally:
            stop_completed.set()

    worker = threading.Thread(target=run_and_stop, name="self-stop-worker")
    worker.start()

    assert stop_completed.wait(timeout=2.0)
    worker.join(timeout=2.0)

    assert not errors
    assert announcer._stop_event.is_set()
    assert announcer._thread is None


def test_create_webcam_app_initializes_discovery_with_webcam_id(full_config, monkeypatch, caplog):
    from pi_camera_in_docker import main

    captured = {}

    class FakeAnnouncer:
        def __init__(
            self,
            *,
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
    discovery_token = "startup-discovery-secret"
    cfg["discovery_token"] = discovery_token
    cfg["discovery_interval_seconds"] = 15.0
    cfg["base_url"] = "http://localhost:8000"
    cfg["mock_camera"] = True

    with caplog.at_level("INFO"):
        app = main.create_webcam_app(cfg)

    assert app.motion_state["discovery_announcer"] is not None
    assert captured["started"] is True
    assert captured["token"] == discovery_token
    assert captured["webcam_id"] == payload["webcam_id"]
    assert captured["payload"] == payload
    assert captured["shutdown_event"] is app.motion_state["discovery_shutdown_event"]
    assert discovery_token not in caplog.text
    assert not [
        record
        for record in caplog.records
        if record.__dict__.get("event") == "discovery_misconfigured"
    ]


def test_create_webcam_app_logs_only_token_presence_when_discovery_is_misconfigured(
    full_config, caplog
):
    """Misconfiguration logs should expose only a false token-presence flag."""
    from pi_camera_in_docker import main

    cfg = dict(full_config)
    cfg["discovery_enabled"] = True
    cfg["discovery_token"] = ""
    cfg["mock_camera"] = True

    with caplog.at_level("WARNING"):
        main.create_webcam_app(cfg)

    records = [
        record
        for record in caplog.records
        if record.__dict__.get("event") == "discovery_misconfigured"
    ]
    assert len(records) == 1
    assert records[0].__dict__["discovery_token_present"] is False
    assert "discovery_token" not in records[0].__dict__


def test_discovery_run_loop_unexpected_exception_continues_with_backoff(monkeypatch):
    from pi_camera_in_docker.discovery import DiscoveryAnnouncer

    shutdown_event = threading.Event()
    announcer = DiscoveryAnnouncer(
        management_url="http://127.0.0.1:8001",
        token="token",
        interval_seconds=10,
        webcam_id="node-unexpected-error",
        payload={"webcam_id": "node-unexpected-error"},
        shutdown_event=shutdown_event,
    )

    wait_calls = []

    def fake_wait_for_next_attempt(wait_seconds: float) -> bool:
        wait_calls.append(wait_seconds)
        return len(wait_calls) >= 3

    announce_calls = {"count": 0}

    def fake_announce_once() -> bool:
        announce_calls["count"] += 1
        if announce_calls["count"] == 1:
            raise RuntimeError("boom")
        return True

    sentry_tags = {}
    captured_exceptions = []

    class FakeScope:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def set_tag(self, key, value):
            sentry_tags[key] = value

        def capture_exception(self, exc):
            captured_exceptions.append(exc)

    monkeypatch.setattr(announcer, "_wait_for_next_attempt", fake_wait_for_next_attempt)
    monkeypatch.setattr(announcer, "_announce_once", fake_announce_once)
    monkeypatch.setattr("pi_camera_in_docker.discovery.random.uniform", lambda _a, _b: 0.0)
    monkeypatch.setattr("pi_camera_in_docker.discovery.sentry_sdk.new_scope", FakeScope)

    announcer._run_loop()

    assert announce_calls["count"] == 2
    assert wait_calls == [0.0, 10.0, 10]
    assert sentry_tags == {
        "component": "discovery",
        "webcam_id": "node-unexpected-error",
    }
    assert len(captured_exceptions) == 1
    assert str(captured_exceptions[0]) == "boom"


def test_discovery_run_loop_adds_scheduling_jitter_to_backoff(monkeypatch):
    """Retry wait combines backoff with fixed, non-security scheduling jitter."""
    from pi_camera_in_docker.discovery import DiscoveryAnnouncer

    announcer = DiscoveryAnnouncer(
        management_url="http://127.0.0.1:8001",
        token="token",
        interval_seconds=10,
        webcam_id="node-scheduling-jitter",
        payload={"webcam_id": "node-scheduling-jitter"},
        shutdown_event=threading.Event(),
    )
    wait_calls = []

    def fake_wait_for_next_attempt(wait_seconds: float) -> bool:
        wait_calls.append(wait_seconds)
        return len(wait_calls) >= 2

    jitter = 1.25
    monkeypatch.setattr(announcer, "_wait_for_next_attempt", fake_wait_for_next_attempt)
    monkeypatch.setattr(announcer, "_announce_once", lambda: False)
    monkeypatch.setattr("pi_camera_in_docker.discovery.random.uniform", lambda _a, _b: jitter)

    announcer._run_loop()

    backoff_seconds = 10.0
    assert wait_calls == [0.0, backoff_seconds + jitter]


def test_discovery_announcer_restart_does_not_reset_app_shutdown_event(monkeypatch):
    from discovery import DiscoveryAnnouncer

    app_shutdown_event = threading.Event()
    app_shutdown_event.set()
    announcer = DiscoveryAnnouncer(
        management_url="http://127.0.0.1:8001",
        token="token",
        interval_seconds=1,
        webcam_id="node-1",
        payload={"webcam_id": "node-1"},
        shutdown_event=app_shutdown_event,
    )

    monkeypatch.setattr(announcer, "_announce_once", lambda: True)

    announcer.start()
    assert app_shutdown_event.is_set()

    announcer.stop(timeout_seconds=1.0)
    assert app_shutdown_event.is_set()


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
    assert not shutdown_event.is_set()

    announcer.start()
    assert not shutdown_event.is_set()
    assert second_start_announced.wait(timeout=2.0)
    assert len(announce_calls) >= 2

    announcer.stop(timeout_seconds=1.0)


def test_discovery_announcer_exits_quickly_when_shutdown_event_set_during_retry_delay(monkeypatch):
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

    announce_attempted = threading.Event()

    def fail_once_then_wait_for_shutdown() -> bool:
        if not announce_attempted.is_set():
            announce_attempted.set()
            return False
        return True

    monkeypatch.setattr(announcer, "_announce_once", fail_once_then_wait_for_shutdown)
    monkeypatch.setattr("discovery.random.uniform", lambda _low, _high: 0.0)

    announcer.start()
    assert announce_attempted.wait(timeout=1.0)
    assert announcer._thread is not None
    thread_ref = announcer._thread
    assert thread_ref.is_alive()

    shutdown_event.set()
    thread_ref.join(timeout=0.75)

    assert not thread_ref.is_alive()

    announcer.stop(timeout_seconds=1.0)
