import importlib
import sys


def test_management_mode_boots_without_camera(monkeypatch):
    monkeypatch.setenv("APP_MODE", "management")
    monkeypatch.setenv("MOTION_IN_OCEAN_MOCK_CAMERA", "false")

    sys.modules.pop("main", None)
    sys.modules.pop("picamera2", None)

    main = importlib.import_module("main")
    client = main.create_management_app(main._load_config()).test_client()

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json["app_mode"] == "management"

    ready = client.get("/ready")
    assert ready.status_code == 200
    assert ready.json["reason"] == "camera_disabled_for_management_mode"

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert metrics.json["camera_mode_enabled"] is False

    stream = client.get("/stream.mjpg")
    assert stream.status_code == 404

    snapshot = client.get("/snapshot.jpg")
    assert snapshot.status_code == 404

    assert "picamera2" not in sys.modules


def test_webcam_mode_env_validation_and_startup(monkeypatch):
    monkeypatch.setenv("APP_MODE", "management")
    monkeypatch.setenv("MOCK_CAMERA", "true")
    monkeypatch.setenv("RESOLUTION", "0x5000")
    monkeypatch.setenv("FPS", "bad")
    monkeypatch.setenv("TARGET_FPS", "also_bad")
    monkeypatch.setenv("JPEG_QUALITY", "1000")
    monkeypatch.setenv("MAX_FRAME_AGE_SECONDS", "-1")
    monkeypatch.setenv("MAX_STREAM_CONNECTIONS", "not_an_int")

    sys.modules.pop("main", None)
    main = importlib.import_module("main")

    cfg = main._load_config()
    assert cfg["resolution"] == (640, 480)
    assert cfg["fps"] == 0
    assert cfg["target_fps"] == 0
    assert cfg["jpeg_quality"] == 90
    assert cfg["max_frame_age_seconds"] == 10.0
    assert cfg["max_stream_connections"] == 10

    cfg["app_mode"] = "webcam"
    cfg["mock_camera"] = True
    app = main.create_webcam_app(cfg)
    ready = app.test_client().get("/ready")
    assert ready.status_code in (200, 503)


def test_root_serves_management_template_in_management_mode(monkeypatch):
    monkeypatch.setenv("APP_MODE", "management")

    sys.modules.pop("main", None)
    main = importlib.import_module("main")
    client = main.create_management_app(main._load_config()).test_client()

    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Node Management" in html
    assert "/static/js/management.js" in html


def test_root_serves_stream_template_in_webcam_mode(monkeypatch):
    monkeypatch.setenv("APP_MODE", "management")
    monkeypatch.setenv("MOCK_CAMERA", "true")

    sys.modules.pop("main", None)
    main = importlib.import_module("main")
    cfg = main._load_config()
    cfg["app_mode"] = "webcam"
    cfg["mock_camera"] = True
    app = main.create_webcam_app(cfg)
    client = app.test_client()

    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "motion-in-ocean - Camera Stream" in html
    assert "/static/js/app.js" in html


def test_request_logging_levels(monkeypatch):
    monkeypatch.setenv("APP_MODE", "management")

    sys.modules.pop("main", None)
    main = importlib.import_module("main")
    client = main.create_management_app(main._load_config()).test_client()

    records = []

    def capture(level, msg, *args, **kwargs):
        records.append((level, msg % args))

    monkeypatch.setattr(main.logger, "log", capture)

    health = client.get("/health")
    metrics = client.get("/metrics")

    assert health.status_code == 200
    assert metrics.status_code == 200

    health_record = next((message for _, message in records if "path=/health" in message), None)
    metrics_record = next((message for _, message in records if "path=/metrics" in message), None)
    health_level = next((level for level, message in records if "path=/health" in message), None)
    metrics_level = next((level for level, message in records if "path=/metrics" in message), None)
    
    assert health_record is not None, "No health endpoint log found"
    assert metrics_record is not None, "No metrics endpoint log found"
    assert health_level is not None, "No health level log found"
    assert metrics_level is not None, "No metrics level log found"

    assert "request method=GET path=/health status=200 latency_ms=" in health_record
    assert "request method=GET path=/metrics status=200 latency_ms=" in metrics_record
    assert health_level == main.logging.DEBUG
    assert metrics_level == main.logging.INFO

