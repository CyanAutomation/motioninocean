import importlib
import sys


def test_management_mode_boots_without_camera(monkeypatch):
    monkeypatch.setenv('APP_MODE', 'management')
    monkeypatch.setenv('MOTION_IN_OCEAN_MOCK_CAMERA', 'false')

    sys.modules.pop('main', None)
    sys.modules.pop('picamera2', None)

    main = importlib.import_module('main')
    client = main.create_management_app(main._load_config()).test_client()

    health = client.get('/health')
    assert health.status_code == 200
    assert health.json['app_mode'] == 'management'

    ready = client.get('/ready')
    assert ready.status_code == 200
    assert ready.json['reason'] == 'camera_disabled_for_management_mode'

    metrics = client.get('/metrics')
    assert metrics.status_code == 200
    assert metrics.json['camera_mode_enabled'] is False

    stream = client.get('/stream.mjpg')
    assert stream.status_code == 404

    snapshot = client.get('/snapshot.jpg')
    assert snapshot.status_code == 404

    assert 'picamera2' not in sys.modules



def test_webcam_mode_env_validation_and_startup(monkeypatch):
    monkeypatch.setenv('APP_MODE', 'management')
    monkeypatch.setenv('MOCK_CAMERA', 'true')
    monkeypatch.setenv('RESOLUTION', '0x5000')
    monkeypatch.setenv('FPS', 'bad')
    monkeypatch.setenv('TARGET_FPS', 'also_bad')
    monkeypatch.setenv('JPEG_QUALITY', '1000')
    monkeypatch.setenv('MAX_FRAME_AGE_SECONDS', '-1')
    monkeypatch.setenv('MAX_STREAM_CONNECTIONS', 'not_an_int')

    sys.modules.pop('main', None)
    main = importlib.import_module('main')

    cfg = main._load_config()
    assert cfg['resolution'] == (640, 480)
    assert cfg['fps'] == 0
    assert cfg['target_fps'] == 0
    assert cfg['jpeg_quality'] == 90
    assert cfg['max_frame_age_seconds'] == 10.0
    assert cfg['max_stream_connections'] == 10

    cfg['app_mode'] = 'webcam_node'
    cfg['mock_camera'] = True
    app = main.create_webcam_node_app(cfg)
    ready = app.test_client().get('/ready')
    assert ready.status_code in (200, 503)
