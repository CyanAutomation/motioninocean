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
