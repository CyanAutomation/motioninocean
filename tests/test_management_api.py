import importlib
import json
import socket
import ssl
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

import pytest
from flask import Flask


# Import workspace root path (WORKSPACE_ROOT is set in conftest.py)
# For module-level imports
workspace_root = Path(__file__).parent.parent


def _new_management_client(monkeypatch, tmp_path, management_token="test-token", webcam_token=""):
    # SET THIS FIRST - before any other monkeypatches to ensure ApplicationSettings reads from tmp_path
    monkeypatch.setenv(
        "MIO_APPLICATION_SETTINGS_PATH",
        str(tmp_path / "application-settings.json"),
    )

    monkeypatch.setenv("MIO_APP_MODE", "management")
    monkeypatch.setenv("MIO_NODE_REGISTRY_PATH", str(tmp_path / "registry.json"))
    monkeypatch.setenv("MIO_MANAGEMENT_AUTH_TOKEN", management_token)
    monkeypatch.setenv("MIO_WEBCAM_CONTROL_PLANE_AUTH_TOKEN", webcam_token)
    monkeypatch.setenv("MIO_NODE_DISCOVERY_SHARED_SECRET", "discovery-secret")

    original_sys_path = sys.path.copy()
    sys.path.insert(
        0, str(workspace_root)
    )  # Add the parent directory of pi_camera_in_docker to sys.path
    try:
        # Clear existing modules to ensure fresh import with new path
        sys.modules.pop("pi_camera_in_docker.main", None)
        sys.modules.pop("pi_camera_in_docker.management_api", None)
        # Import as a package module
        main = importlib.import_module("pi_camera_in_docker.main")
        management_api = importlib.import_module("pi_camera_in_docker.management_api")
        client = main.create_management_app(main._load_config()).test_client()
        return client, management_api
    finally:
        sys.path = original_sys_path


def _new_webcam_contract_client(auth_token=""):
    from pi_camera_in_docker import shared

    app = Flask(__name__)
    state = {
        "app_mode": "webcam",
        "recording_started": threading.Event(),
        "max_frame_age_seconds": 10.0,
        "max_stream_connections": 8,
        "connection_tracker": None,
    }
    shared.register_webcam_control_plane_auth(app, auth_token, lambda: "webcam")
    shared.register_shared_routes(
        app, state, get_stream_status=lambda: {"current_fps": 0.0, "last_frame_age_seconds": None}
    )
    return app.test_client()


def test_api_status_ignores_api_test_mode_when_lock_is_missing():
    from pi_camera_in_docker import shared

    app = Flask(__name__)
    state = {
        "app_mode": "webcam",
        "recording_started": threading.Event(),
        "max_frame_age_seconds": 10.0,
        "max_stream_connections": 8,
        "connection_tracker": None,
        "api_test": {
            "enabled": True,
            "active": True,
            # lock intentionally omitted to ensure endpoint remains resilient
        },
    }

    shared.register_shared_routes(
        app,
        state,
        get_stream_status=lambda: {"current_fps": 0.0, "last_frame_age_seconds": None},
    )
    response = app.test_client().get("/api/status")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "degraded"
    assert payload["camera_active"] is False
    assert "api_test" not in payload


def test_api_status_returns_current_api_test_scenario_when_inactive():
    from pi_camera_in_docker import shared

    app = Flask(__name__)
    state = {
        "app_mode": "webcam",
        "recording_started": threading.Event(),
        "max_frame_age_seconds": 10.0,
        "max_stream_connections": 8,
        "connection_tracker": None,
        "api_test": {
            "enabled": True,
            "active": False,
            "lock": threading.RLock(),
            "scenario_list": [
                {
                    "status": "ok",
                    "stream_available": True,
                    "camera_active": True,
                    "fps": 30.0,
                    "connections": {"current": 2, "max": 8},
                },
                {
                    "status": "degraded",
                    "stream_available": False,
                    "camera_active": False,
                    "fps": 0.0,
                    "connections": {"current": 0, "max": 8},
                },
            ],
            "current_state_index": 1,
            "cycle_interval_seconds": 0.01,
            "last_transition_monotonic": 0.0,
        },
    }

    shared.register_shared_routes(
        app,
        state,
        get_stream_status=lambda: {"current_fps": 0.0, "last_frame_age_seconds": None},
    )
    response = app.test_client().get("/api/status")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "degraded"
    assert payload["api_test"] == {
        "enabled": True,
        "active": False,
        "state_index": 1,
        "state_name": "degraded",
        "next_transition_seconds": None,
    }
    assert state["api_test"]["current_state_index"] == 1


def test_settings_changes_endpoint_compares_resolution_values(monkeypatch, tmp_path):
    monkeypatch.setenv("MIO_RESOLUTION", "1280x720")
    client, _ = _new_management_client(monkeypatch, tmp_path)

    save_response = client.patch(
        "/api/settings",
        json={"camera": {"resolution": "1920x1080"}},
    )
    assert save_response.status_code in (200, 422)

    response = client.get("/api/settings/changes")
    assert response.status_code == 200

    overridden = response.get_json()["overridden"]
    assert {
        "category": "camera",
        "key": "resolution",
        "value": "1920x1080",
        "env_value": "1280x720",
    } in overridden


def test_settings_changes_endpoint_handles_invalid_resolution_env(monkeypatch, tmp_path):
    monkeypatch.setenv("MIO_RESOLUTION", "invalid")
    client, _ = _new_management_client(monkeypatch, tmp_path)

    save_response = client.patch(
        "/api/settings",
        json={"camera": {"resolution": "800x600"}},
    )
    assert save_response.status_code in (200, 422)

    response = client.get("/api/settings/changes")
    assert response.status_code == 200

    overridden = response.get_json()["overridden"]
    assert {
        "category": "camera",
        "key": "resolution",
        "value": "800x600",
        "env_value": "640x480",
    } in overridden


def test_settings_changes_endpoint_handles_invalid_numeric_env(monkeypatch, tmp_path):
    monkeypatch.setenv("MIO_FPS", "invalid-fps")
    monkeypatch.setenv("MIO_JPEG_QUALITY", "invalid-jpeg")
    monkeypatch.setenv("MIO_MAX_STREAM_CONNECTIONS", "invalid-connections")
    monkeypatch.setenv("MIO_MAX_FRAME_AGE_SECONDS", "invalid-age")
    monkeypatch.setenv("MIO_DISCOVERY_INTERVAL_SECONDS", "invalid-interval")
    client, _ = _new_management_client(monkeypatch, tmp_path)

    save_response = client.patch(
        "/api/settings",
        json={
            "camera": {
                "fps": 12,
                "jpeg_quality": 77,
                "max_stream_connections": 5,
                "max_frame_age_seconds": 4.5,
            },
            "discovery": {
                "discovery_interval_seconds": 22.5,
            },
        },
    )
    assert save_response.status_code in (200, 422)

    response = client.get("/api/settings/changes")
    assert response.status_code == 200

    overridden = response.get_json()["overridden"]
    by_key = {(item["category"], item["key"]): item for item in overridden}

    assert by_key[("camera", "fps")]["value"] == 12
    assert by_key[("camera", "fps")]["env_value"] == 24

    assert by_key[("camera", "jpeg_quality")]["value"] == 77
    assert isinstance(by_key[("camera", "jpeg_quality")]["env_value"], int)

    max_stream = by_key.get(("camera", "max_stream_connections"))
    if max_stream is not None:
        assert max_stream["value"] == 5
        assert isinstance(max_stream["env_value"], int)

    assert by_key[("camera", "max_frame_age_seconds")]["value"] == 4.5
    assert by_key[("camera", "max_frame_age_seconds")]["env_value"] == 10

    assert by_key[("discovery", "discovery_interval_seconds")]["value"] == 22.5
    assert by_key[("discovery", "discovery_interval_seconds")]["env_value"] == 30


def test_settings_patch_rejects_malformed_json(monkeypatch, tmp_path):
    client, _ = _new_management_client(monkeypatch, tmp_path)

    response = client.patch(
        "/api/settings",
        data='{"camera": {"fps": 30',
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "INVALID_JSON",
        "message": "Request body must be valid JSON.",
    }


def test_settings_patch_response_reflects_persisted_state(monkeypatch, tmp_path):
    client, _ = _new_management_client(monkeypatch, tmp_path)

    before = client.get("/api/settings")
    assert before.status_code == 200
    before_payload = before.get_json()

    response = client.patch(
        "/api/settings",
        json={"camera": {"jpeg_quality": 70}},
    )
    assert response.status_code == 200
    payload = response.get_json()

    after = client.get("/api/settings")
    assert after.status_code == 200
    after_payload = after.get_json()

    assert payload["modified_by"] == after_payload["modified_by"] == "api_patch"
    assert after_payload["settings"]["camera"]["jpeg_quality"] == 70
    assert payload["last_modified"] == after_payload["last_modified"]
    assert payload["last_modified"] != before_payload["last_modified"]


def test_settings_patch_requires_restart_response_reflects_persisted_state(monkeypatch, tmp_path):
    client, _ = _new_management_client(monkeypatch, tmp_path)

    before = client.get("/api/settings")
    assert before.status_code == 200
    before_payload = before.get_json()

    response = client.patch(
        "/api/settings",
        json={"camera": {"resolution": "800x600"}},
    )
    assert response.status_code == 422
    payload = response.get_json()

    after = client.get("/api/settings")
    assert after.status_code == 200
    after_payload = after.get_json()

    assert payload["requires_restart"] is True
    assert "camera.resolution" in payload["modified_on_restart"]
    assert payload["modified_by"] == after_payload["modified_by"] == "api_patch"
    assert after_payload["settings"]["camera"]["resolution"] == "800x600"
    assert payload["last_modified"] == after_payload["last_modified"]
    assert payload["last_modified"] != before_payload["last_modified"]


def test_settings_endpoint_returns_effective_runtime_values(monkeypatch, tmp_path):
    monkeypatch.setenv("MIO_RESOLUTION", "1280x720")
    monkeypatch.setenv("MIO_FPS", "24")
    monkeypatch.setenv("MIO_JPEG_QUALITY", "88")
    monkeypatch.setenv("MIO_MAX_STREAM_CONNECTIONS", "6")
    monkeypatch.setenv("MIO_MAX_FRAME_AGE_SECONDS", "12")
    monkeypatch.setenv("MIO_LOG_LEVEL", "WARNING")
    monkeypatch.setenv("MIO_LOG_FORMAT", "json")
    monkeypatch.setenv("MIO_LOG_INCLUDE_IDENTIFIERS", "false")
    monkeypatch.setenv("MIO_DISCOVERY_ENABLED", "false")
    monkeypatch.setenv("MIO_DISCOVERY_MANAGEMENT_URL", "http://env.example:8001")
    monkeypatch.setenv("MIO_DISCOVERY_TOKEN", "env-token")
    monkeypatch.setenv("MIO_DISCOVERY_INTERVAL_SECONDS", "45")

    client, _ = _new_management_client(monkeypatch, tmp_path)

    patch_response = client.patch(
        "/api/settings",
        json={
            "camera": {"fps": 30},
            "logging": {"log_level": "DEBUG"},
            "discovery": {"discovery_enabled": True},
        },
    )
    assert patch_response.status_code in (200, 422)

    response = client.get("/api/settings")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["source"] == "merged"

    settings = payload["settings"]
    assert settings["camera"] == {
        "resolution": "1280x720",
        "fps": 30,
        "jpeg_quality": 88,
        "max_stream_connections": 6,
        "max_frame_age_seconds": 12.0,
    }
    assert settings["logging"] == {
        "log_level": "DEBUG",
        "log_format": "json",
        "log_include_identifiers": False,
    }
    assert settings["discovery"] == {
        "discovery_enabled": True,
        "discovery_management_url": "http://env.example:8001",
        "discovery_token": "env-token",
        "discovery_interval_seconds": 45.0,
    }


def test_settings_patch_concurrent_overlapping_updates_are_merged(monkeypatch, tmp_path):
    client_a, _ = _new_management_client(monkeypatch, tmp_path)
    client_b, _ = _new_management_client(monkeypatch, tmp_path)

    start = threading.Barrier(2)
    statuses = []

    def patch_fps():
        start.wait()
        response = client_a.patch(
            "/api/settings",
            json={"camera": {"fps": 55}},
        )
        statuses.append(response.status_code)

    def patch_quality():
        start.wait()
        response = client_b.patch(
            "/api/settings",
            json={"camera": {"jpeg_quality": 72}},
        )
        statuses.append(response.status_code)

    thread_a = threading.Thread(target=patch_fps)
    thread_b = threading.Thread(target=patch_quality)
    thread_a.start()
    thread_b.start()
    thread_a.join()
    thread_b.join()

    assert len(statuses) == 2
    assert all(status in (200, 422) for status in statuses)

    final_client, _ = _new_management_client(monkeypatch, tmp_path)
    final_response = final_client.get("/api/settings")
    assert final_response.status_code == 200
    final_settings = final_response.get_json()["settings"]["camera"]
    assert final_settings["fps"] == 55
    assert final_settings["jpeg_quality"] == 72


def _auth_headers(token="test-token"):
    return {"Authorization": f"Bearer {token}"}


def test_node_crud_and_overview(monkeypatch, tmp_path):
    client, _ = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "id": "node-1",
        "name": "Front Door",
        "base_url": "http://127.0.0.1:65534",
        "auth": {"type": "none"},
        "labels": {"location": "entry"},
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "capabilities": ["stream", "metrics"],
        "transport": "http",
    }

    created = client.post("/api/webcams", json=payload, headers=_auth_headers())
    assert created.status_code == 201
    assert created.json["id"] == "node-1"
    assert created.json["discovery"]["source"] == "manual"
    assert created.json["discovery"]["approved"] is True

    listed = client.get("/api/webcams", headers=_auth_headers())
    assert listed.status_code == 200
    assert len(listed.json["webcams"]) == 1

    updated = client.put(
        "/api/webcams/node-1", json={"name": "Front Door Cam"}, headers=_auth_headers()
    )
    assert updated.status_code == 200
    assert updated.json["name"] == "Front Door Cam"

    status = client.get("/api/webcams/node-1/status", headers=_auth_headers())
    assert status.status_code == 503
    assert status.json["error"]["code"] == "SSRF_BLOCKED"

    overview = client.get("/api/management/overview", headers=_auth_headers())
    assert overview.status_code == 200
    assert overview.json["summary"]["total_webcams"] == 1
    assert overview.json["summary"]["unavailable_webcams"] == 1
    assert overview.json["summary"]["healthy_webcams"] == 0

    deleted = client.delete("/api/webcams/node-1", headers=_auth_headers())
    assert deleted.status_code == 204


def test_validation_and_transport_errors(monkeypatch, tmp_path):
    client, _ = _new_management_client(monkeypatch, tmp_path)

    invalid = client.post("/api/webcams", json={"id": "only-id"}, headers=_auth_headers())
    assert invalid.status_code == 400
    assert invalid.json["error"]["code"] == "VALIDATION_ERROR"

    payload = {
        "id": "node-2",
        "name": "Docker Node",
        "base_url": "docker://proxy:2375/container-id",
        "auth": {"type": "none"},
        "labels": {},
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "capabilities": ["stream"],
        "transport": "docker",
    }
    assert (
        client.post(
            "/api/webcams",
            json=payload,
            headers={"Authorization": "Bearer test-token"},
        ).status_code
        == 201
    )

    invalid_docker_create = {
        "id": "node-2-invalid",
        "name": "Docker Node Invalid",
        "base_url": "docker://proxy/container-id",
        "auth": {"type": "none"},
        "labels": {},
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "capabilities": ["stream"],
        "transport": "docker",
    }
    invalid_create = client.post(
        "/api/webcams", json=invalid_docker_create, headers=_auth_headers()
    )
    assert invalid_create.status_code == 400
    assert invalid_create.json["error"]["code"] == "VALIDATION_ERROR"
    assert "docker URL must include port" in invalid_create.json["error"]["message"]

    invalid_update = client.put(
        "/api/webcams/node-2",
        json={"base_url": "docker://proxy:2375"},
        headers=_auth_headers(),
    )
    assert invalid_update.status_code == 400
    assert invalid_update.json["error"]["code"] == "VALIDATION_ERROR"
    assert "docker URL must include container ID" in invalid_update.json["error"]["message"]

    action = client.post("/api/webcams/node-2/actions/restart", json={}, headers=_auth_headers())
    assert action.status_code == 400
    assert action.json["error"]["code"] == "TRANSPORT_UNSUPPORTED"


def test_create_node_rejects_unmigratable_legacy_basic_auth(monkeypatch, tmp_path):
    client, _ = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "id": "node-legacy-auth",
        "name": "Legacy Auth",
        "base_url": "http://example.com",
        "auth": {"type": "basic", "username": "camera", "password": "secret"},
        "labels": {},
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "capabilities": ["stream"],
        "transport": "http",
    }

    response = client.post("/api/webcams", json=payload, headers=_auth_headers())
    assert response.status_code == 400
    assert response.json["error"]["code"] == "VALIDATION_ERROR"
    assert (
        "auth.type='basic' cannot be auto-migrated without an API token"
        in response.json["error"]["message"]
    )


def test_ssrf_protection_blocks_local_targets(monkeypatch, tmp_path):
    client, _ = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "id": "node-3",
        "name": "Internal Node",
        "base_url": "http://127.0.0.1:8080",
        "auth": {"type": "none"},
        "labels": {},
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "capabilities": ["metrics"],
        "transport": "http",
    }
    assert (
        client.post(
            "/api/webcams",
            json=payload,
            headers={"Authorization": "Bearer test-token"},
        ).status_code
        == 201
    )

    status = client.get("/api/webcams/node-3/status", headers=_auth_headers())
    assert status.status_code == 503
    assert status.json["error"]["code"] == "SSRF_BLOCKED"
    assert "SSRF protection" in status.json["error"]["details"]["reason"]
    assert status.json["error"]["details"]["category"] == "ssrf_blocked"


def test_corrupted_registry_file_returns_500_error_payload(monkeypatch, tmp_path):
    registry_path = tmp_path / "registry.json"
    registry_path.write_text("{invalid json", encoding="utf-8")

    monkeypatch.setenv("MIO_APP_MODE", "management")
    monkeypatch.setenv("MIO_NODE_REGISTRY_PATH", str(registry_path))
    monkeypatch.setenv("MIO_MANAGEMENT_AUTH_TOKEN", "test-token")
    original_sys_path = sys.path.copy()
    sys.path.insert(
        0, str(workspace_root)
    )  # Add the parent directory of pi_camera_in_docker to sys.path
    try:
        sys.modules.pop("pi_camera_in_docker.main", None)
        sys.modules.pop("pi_camera_in_docker.management_api", None)
        main = importlib.import_module("pi_camera_in_docker.main")
        client = main.create_management_app(main._load_config()).test_client()
    finally:
        sys.path = original_sys_path

    listed = client.get("/api/webcams", headers=_auth_headers())
    assert listed.status_code == 500
    assert listed.json["error"]["code"] == "REGISTRY_CORRUPTED"
    assert listed.json["error"]["details"]["reason"] == "invalid registry json"

    overview = client.get("/api/management/overview", headers=_auth_headers())
    assert overview.status_code == 500
    assert overview.json["error"]["code"] == "REGISTRY_CORRUPTED"


def test_ssrf_protection_blocks_ipv6_mapped_loopback(monkeypatch, tmp_path):
    client, _ = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "id": "node-4",
        "name": "Mapped Loopback",
        "base_url": "http://[::ffff:127.0.0.1]:8080",
        "auth": {"type": "none"},
        "labels": {},
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "capabilities": ["metrics"],
        "transport": "http",
    }
    assert (
        client.post(
            "/api/webcams",
            json=payload,
            headers={"Authorization": "Bearer test-token"},
        ).status_code
        == 201
    )

    status = client.get("/api/webcams/node-4/status", headers=_auth_headers())
    assert status.status_code == 503
    assert status.json["error"]["code"] == "SSRF_BLOCKED"
    assert "SSRF protection" in status.json["error"]["details"]["reason"]
    assert status.json["error"]["details"]["category"] == "ssrf_blocked"


def test_ssrf_protection_blocks_metadata_ip_literal(monkeypatch, tmp_path):
    client, _ = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "id": "node-5",
        "name": "Metadata Target",
        "base_url": "http://169.254.169.254",
        "auth": {"type": "none"},
        "labels": {},
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "capabilities": ["metrics"],
        "transport": "http",
    }
    assert (
        client.post(
            "/api/webcams",
            json=payload,
            headers={"Authorization": "Bearer test-token"},
        ).status_code
        == 201
    )

    status = client.get("/api/webcams/node-5/status", headers=_auth_headers())
    assert status.status_code == 503
    assert status.json["error"]["code"] == "SSRF_BLOCKED"
    assert "SSRF protection" in status.json["error"]["details"]["reason"]
    assert status.json["error"]["details"]["category"] == "ssrf_blocked"


def test_management_endpoints_do_not_accept_webcam_control_plane_token(monkeypatch, tmp_path):
    client, _ = _new_management_client(
        monkeypatch,
        tmp_path,
        management_token="management-only-token",
        webcam_token="webcam-only-token",
    )

    response = client.get("/api/webcams", headers={"Authorization": "Bearer webcam-only-token"})

    assert response.status_code == 401
    assert response.json["error"]["code"] == "UNAUTHORIZED"


def test_docker_transport_allows_any_valid_token(monkeypatch, tmp_path):
    monkeypatch.setenv("MANAGEMENT_AUTH_REQUIRED", "true")
    client, _ = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "id": "node-docker-shared",
        "name": "Docker Shared Access",
        "base_url": "docker://proxy:2375/container-id",
        "auth": {"type": "none"},
        "labels": {},
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "capabilities": ["stream"],
        "transport": "docker",
    }

    unauthorized = client.post("/api/webcams", json=payload)
    assert unauthorized.status_code == 401
    assert unauthorized.json["error"]["code"] == "UNAUTHORIZED"

    invalid_token = client.post(
        "/api/webcams",
        json=payload,
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert invalid_token.status_code == 401
    assert invalid_token.json["error"]["code"] == "UNAUTHORIZED"

    authorized = client.post(
        "/api/webcams",
        json=payload,
        headers={"Authorization": "Bearer test-token"},
    )
    assert authorized.status_code == 201
    assert authorized.json["id"] == "node-docker-shared"


def test_update_node_returns_404_when_node_disappears_during_update(monkeypatch, tmp_path):
    from pi_camera_in_docker import management_api

    original_update_webcam = management_api.FileWebcamRegistry.update_webcam

    def flaky_update_node(self, webcam_id, patch):
        if webcam_id == "node-race":
            raise KeyError(webcam_id)
        return original_update_webcam(self, webcam_id, patch)

    monkeypatch.setattr(management_api.FileWebcamRegistry, "update_webcam", flaky_update_node)
    client, _ = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "id": "node-race",
        "name": "Race Node",
        "base_url": "http://example.com",
        "auth": {"type": "none"},
        "labels": {},
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "capabilities": ["stream"],
        "transport": "http",
    }

    created = client.post("/api/webcams", json=payload, headers=_auth_headers())
    assert created.status_code == 201

    response = client.put(
        "/api/webcams/node-race", json={"name": "Updated Name"}, headers=_auth_headers()
    )
    assert response.status_code == 404
    assert response.json["error"]["code"] == "WEBCAM_NOT_FOUND"


def test_discovery_announce_creates_then_updates_node(monkeypatch, tmp_path):
    monkeypatch.setenv("MIO_NODE_DISCOVERY_SHARED_SECRET", "discovery-secret")
    client, _ = _new_management_client(monkeypatch, tmp_path)

    create_payload = {
        "webcam_id": "node-discovery-1",
        "name": "Discovery Node",
        "base_url": "http://example.com",
        "transport": "http",
        "capabilities": ["stream", "metrics"],
    }

    created = client.post(
        "/api/discovery/announce",
        json=create_payload,
        headers={"Authorization": "Bearer discovery-secret"},
    )
    assert created.status_code == 201
    assert created.json["upserted"] == "created"
    assert created.json["node"]["id"] == "node-discovery-1"
    assert created.json["node"]["discovery"]["source"] == "discovered"
    assert created.json["node"]["discovery"]["approved"] is False
    first_seen = created.json["node"]["discovery"]["first_seen"]
    first_announce = created.json["node"]["discovery"]["last_announce_at"]

    updated = client.post(
        "/api/discovery/announce",
        json={
            **create_payload,
            "name": "Discovery Node Updated",
            "labels": {"site": "lab"},
            "auth": {"type": "bearer", "token": "node-api-token"},
        },
        headers={"Authorization": "Bearer discovery-secret"},
    )
    assert updated.status_code == 200
    assert updated.json["upserted"] == "updated"
    assert updated.json["node"]["name"] == "Discovery Node Updated"
    assert updated.json["node"]["labels"] == {"site": "lab"}
    assert updated.json["node"]["auth"]["type"] == "bearer"
    assert updated.json["node"]["discovery"]["first_seen"] == first_seen
    assert updated.json["node"]["discovery"]["last_announce_at"] != first_announce


def test_discovery_announce_update_repairs_incomplete_discovery_metadata(monkeypatch, tmp_path):
    monkeypatch.setenv("MIO_NODE_DISCOVERY_SHARED_SECRET", "discovery-secret")
    client, _ = _new_management_client(monkeypatch, tmp_path)

    create_payload = {
        "webcam_id": "node-discovery-incomplete-metadata",
        "name": "Discovery Incomplete",
        "base_url": "http://example.com",
        "transport": "http",
        "capabilities": ["stream"],
    }

    created = client.post(
        "/api/discovery/announce",
        json=create_payload,
        headers={"Authorization": "Bearer discovery-secret"},
    )
    assert created.status_code == 201

    approve = client.post(
        "/api/webcams/node-discovery-incomplete-metadata/discovery/approve",
        headers=_auth_headers(),
    )
    assert approve.status_code == 200

    registry_path = tmp_path / "registry.json"
    registry_data = json.loads(registry_path.read_text())
    node = registry_data["nodes"][0]
    node["discovery"] = {
        "source": "discovered",
        "approved": True,
    }
    registry_path.write_text(json.dumps(registry_data, indent=2))

    updated = client.post(
        "/api/discovery/announce",
        json={**create_payload, "name": "Discovery Incomplete Updated"},
        headers={"Authorization": "Bearer discovery-secret"},
    )
    assert updated.status_code == 200
    assert updated.json["upserted"] == "updated"
    assert updated.json["node"]["discovery"]["first_seen"] is not None
    assert updated.json["node"]["discovery"]["last_announce_at"] is not None
    assert updated.json["node"]["discovery"]["approved"] is True


def test_discovery_announce_parallel_requests_do_not_duplicate_error(monkeypatch, tmp_path):
    monkeypatch.setenv("MIO_NODE_DISCOVERY_SHARED_SECRET", "discovery-secret")
    client, _ = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "webcam_id": "node-discovery-parallel",
        "name": "Discovery Parallel",
        "base_url": "http://example.com",
        "transport": "http",
        "capabilities": ["stream"],
    }

    barrier = threading.Barrier(2)
    responses = []

    def announce_once():
        barrier.wait()
        response = client.post(
            "/api/discovery/announce",
            json=payload,
            headers={"Authorization": "Bearer discovery-secret"},
        )
        responses.append(response)

    t1 = threading.Thread(target=announce_once)
    t2 = threading.Thread(target=announce_once)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    statuses = sorted(response.status_code for response in responses)
    assert statuses == [200, 201]
    assert all(
        response.json.get("error", {}).get("code") != "VALIDATION_ERROR" for response in responses
    )


def test_discovery_announce_requires_bearer_token(monkeypatch, tmp_path):
    monkeypatch.setenv("MIO_NODE_DISCOVERY_SHARED_SECRET", "discovery-secret")
    client, _ = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "webcam_id": "node-discovery-2",
        "name": "Discovery Node",
        "base_url": "http://example.com",
        "transport": "http",
        "capabilities": ["stream"],
    }

    missing = client.post("/api/discovery/announce", json=payload)
    assert missing.status_code == 401
    assert missing.json["error"]["code"] == "UNAUTHORIZED"

    invalid = client.post(
        "/api/discovery/announce",
        json=payload,
        headers={"Authorization": "Bearer wrong-secret"},
    )
    assert invalid.status_code == 401
    assert invalid.json["error"]["code"] == "UNAUTHORIZED"


def test_discovery_announce_blocks_private_ip_without_opt_in(monkeypatch, tmp_path):
    monkeypatch.setenv("MIO_NODE_DISCOVERY_SHARED_SECRET", "discovery-secret")
    monkeypatch.delenv("MIO_ALLOW_PRIVATE_IPS", raising=False)
    client, _ = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "webcam_id": "node-discovery-private-blocked",
        "name": "Discovery Node Private",
        "base_url": "http://192.168.1.50:8000",
        "transport": "http",
        "capabilities": ["stream"],
    }

    blocked = client.post(
        "/api/discovery/announce",
        json=payload,
        headers={"Authorization": "Bearer discovery-secret"},
    )

    assert blocked.status_code == 403
    assert blocked.json["error"]["code"] == "DISCOVERY_PRIVATE_IP_BLOCKED"
    assert blocked.json["error"]["details"]["required_setting"] == "MIO_ALLOW_PRIVATE_IPS=true"


def test_discovery_announce_allows_private_ip_with_opt_in(monkeypatch, tmp_path):
    monkeypatch.setenv("MIO_NODE_DISCOVERY_SHARED_SECRET", "discovery-secret")
    monkeypatch.setenv("MIO_ALLOW_PRIVATE_IPS", "true")
    client, _ = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "webcam_id": "node-discovery-private-allowed",
        "name": "Discovery Node Private Allowed",
        "base_url": "http://192.168.1.51:8000",
        "transport": "http",
        "capabilities": ["stream"],
    }

    created = client.post(
        "/api/discovery/announce",
        json=payload,
        headers={"Authorization": "Bearer discovery-secret"},
    )

    assert created.status_code == 201
    assert created.json["node"]["id"] == "node-discovery-private-allowed"


def test_allow_private_ips_uses_canonical_env_var_precedence(monkeypatch, tmp_path, caplog):
    monkeypatch.setenv("MIO_NODE_DISCOVERY_SHARED_SECRET", "discovery-secret")
    monkeypatch.setenv("MIO_ALLOW_PRIVATE_IPS", "true")
    monkeypatch.setenv("MOTION_IN_OCEAN_ALLOW_PRIVATE_IPS", "false")

    caplog.set_level("WARNING")
    client, management_api = _new_management_client(monkeypatch, tmp_path)

    assert management_api.ALLOW_PRIVATE_IPS is True
    assert (
        "Both MIO_ALLOW_PRIVATE_IPS and deprecated MOTION_IN_OCEAN_ALLOW_PRIVATE_IPS "
        "are set with different values; using MIO_ALLOW_PRIVATE_IPS." in caplog.text
    )

    payload = {
        "webcam_id": "node-discovery-private-canonical-precedence",
        "name": "Discovery Node Private Allowed",
        "base_url": "http://192.168.1.52:8000",
        "transport": "http",
        "capabilities": ["stream"],
    }

    created = client.post(
        "/api/discovery/announce",
        json=payload,
        headers={"Authorization": "Bearer discovery-secret"},
    )

    assert created.status_code == 201
    assert created.json["node"]["id"] == "node-discovery-private-canonical-precedence"


def test_allow_private_ips_legacy_env_var_logs_deprecation(monkeypatch, tmp_path, caplog):
    monkeypatch.setenv("MIO_NODE_DISCOVERY_SHARED_SECRET", "discovery-secret")
    monkeypatch.delenv("MIO_ALLOW_PRIVATE_IPS", raising=False)
    monkeypatch.setenv("MOTION_IN_OCEAN_ALLOW_PRIVATE_IPS", "true")

    caplog.set_level("WARNING")
    client, management_api = _new_management_client(monkeypatch, tmp_path)

    assert management_api.ALLOW_PRIVATE_IPS is True
    assert (
        "Environment variable MOTION_IN_OCEAN_ALLOW_PRIVATE_IPS is deprecated; "
        "please migrate to MIO_ALLOW_PRIVATE_IPS." in caplog.text
    )

    payload = {
        "webcam_id": "node-discovery-private-legacy-allowed",
        "name": "Discovery Node Private Legacy Allowed",
        "base_url": "http://192.168.1.53:8000",
        "transport": "http",
        "capabilities": ["stream"],
    }

    created = client.post(
        "/api/discovery/announce",
        json=payload,
        headers={"Authorization": "Bearer discovery-secret"},
    )

    assert created.status_code == 201
    assert created.json["node"]["id"] == "node-discovery-private-legacy-allowed"


def test_discovery_private_ip_policy_updates_between_requests(monkeypatch, tmp_path):
    monkeypatch.setenv("MIO_NODE_DISCOVERY_SHARED_SECRET", "discovery-secret")
    monkeypatch.delenv("MIO_ALLOW_PRIVATE_IPS", raising=False)
    monkeypatch.delenv("MOTION_IN_OCEAN_ALLOW_PRIVATE_IPS", raising=False)
    client, _ = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "webcam_id": "node-discovery-toggle-policy",
        "name": "Discovery Node Toggle",
        "base_url": "http://192.168.1.60:8000",
        "transport": "http",
        "capabilities": ["stream"],
    }

    blocked = client.post(
        "/api/discovery/announce",
        json=payload,
        headers={"Authorization": "Bearer discovery-secret"},
    )
    assert blocked.status_code == 403
    assert blocked.json["error"]["code"] == "DISCOVERY_PRIVATE_IP_BLOCKED"

    monkeypatch.setenv("MIO_ALLOW_PRIVATE_IPS", "true")
    allowed = client.post(
        "/api/discovery/announce",
        json=payload,
        headers={"Authorization": "Bearer discovery-secret"},
    )
    assert allowed.status_code == 201
    assert allowed.json["node"]["id"] == "node-discovery-toggle-policy"


def test_is_blocked_address_honors_legacy_env_var(monkeypatch, tmp_path):
    monkeypatch.delenv("MIO_ALLOW_PRIVATE_IPS", raising=False)
    monkeypatch.delenv("MOTION_IN_OCEAN_ALLOW_PRIVATE_IPS", raising=False)
    _client, management_api = _new_management_client(monkeypatch, tmp_path)

    assert management_api._is_blocked_address("192.168.1.10") is True

    monkeypatch.setenv("MOTION_IN_OCEAN_ALLOW_PRIVATE_IPS", "1")
    assert management_api._is_blocked_address("192.168.1.10") is False


def test_is_blocked_address_prefers_canonical_over_legacy(monkeypatch, tmp_path, caplog):
    monkeypatch.setenv("MIO_ALLOW_PRIVATE_IPS", "false")
    monkeypatch.setenv("MOTION_IN_OCEAN_ALLOW_PRIVATE_IPS", "true")
    caplog.set_level("WARNING")
    _client, management_api = _new_management_client(monkeypatch, tmp_path)

    assert management_api._is_blocked_address("192.168.1.10") is True
    assert (
        "Both MIO_ALLOW_PRIVATE_IPS and deprecated MOTION_IN_OCEAN_ALLOW_PRIVATE_IPS "
        "are set with different values; using MIO_ALLOW_PRIVATE_IPS." in caplog.text
    )


def test_discovery_announce_validates_payload(monkeypatch, tmp_path):
    monkeypatch.setenv("MIO_NODE_DISCOVERY_SHARED_SECRET", "discovery-secret")
    client, _ = _new_management_client(monkeypatch, tmp_path)

    invalid = client.post(
        "/api/discovery/announce",
        json={"webcam_id": "node-discovery-3"},
        headers={"Authorization": "Bearer discovery-secret"},
    )
    assert invalid.status_code == 400
    assert invalid.json["error"]["code"] == "VALIDATION_ERROR"


def test_discovery_approval_endpoint(monkeypatch, tmp_path):
    monkeypatch.setenv("MIO_NODE_DISCOVERY_SHARED_SECRET", "discovery-secret")
    client, _ = _new_management_client(monkeypatch, tmp_path)

    announce_payload = {
        "webcam_id": "node-discovery-approval",
        "name": "Discovery Pending",
        "base_url": "http://example.com",
        "transport": "http",
        "capabilities": ["stream"],
    }

    created = client.post(
        "/api/discovery/announce",
        json=announce_payload,
        headers={"Authorization": "Bearer discovery-secret"},
    )
    assert created.status_code == 201
    assert created.json["node"]["discovery"]["approved"] is False

    approved = client.post(
        "/api/webcams/node-discovery-approval/discovery/approve",
        headers=_auth_headers(),
    )
    assert approved.status_code == 200
    assert approved.json["node"]["discovery"]["approved"] is True

    rejected = client.post(
        "/api/webcams/node-discovery-approval/discovery/reject",
        headers=_auth_headers(),
    )
    assert rejected.status_code == 200
    assert rejected.json["node"]["discovery"]["approved"] is False


def test_request_json_sets_authorization_header_by_auth_mode(monkeypatch):
    from pi_camera_in_docker import management_api

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"status":"ok"}'

    captured = {"headers": []}

    def fake_getaddrinfo(host, port, proto):
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 80))]

    class FakeHTTPConnection:
        def __init__(self, host, port, connect_host, timeout):
            _ = (host, port, connect_host, timeout)

        def request(self, method, target, body=None, headers=None):
            _ = (method, target, body)
            captured["headers"].append(headers.get("Authorization"))

        def getresponse(self):
            return FakeResponse()

        def close(self):
            return None

    monkeypatch.setattr(management_api.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(management_api, "_PinnedHTTPConnection", FakeHTTPConnection)

    cases = [
        ({"type": "bearer", "token": "node-token"}, "Bearer node-token"),
        ({"type": "bearer"}, None),
        ({"type": "basic", "encoded": "abc", "username": "camera", "password": "secret"}, None),
    ]

    for auth_payload, expected_auth_header in cases:
        captured["headers"].clear()
        webcam = {"base_url": "http://example.com", "auth": auth_payload}
        status_code, _ = management_api._request_json(webcam, "GET", "/api/status")
        assert status_code == 200
        assert captured["headers"] == [expected_auth_header]


def test_node_status_returns_node_unauthorized_when_upstream_rejects_token(monkeypatch, tmp_path):
    client, management_api = _new_management_client(monkeypatch, tmp_path)
    payload = {
        "id": "node-auth-fail",
        "name": "Auth Fail Node",
        "base_url": "http://example.com",
        "auth": {"type": "bearer", "token": "wrong-token"},
        "labels": {},
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "capabilities": ["stream"],
        "transport": "http",
    }
    created = client.post("/api/webcams", json=payload, headers=_auth_headers())
    assert created.status_code == 201

    def fake_request_json(node, method, path, body=None):
        assert path == "/api/status"
        return 401, {"status": "unauthorized"}

    monkeypatch.setattr(management_api, "_request_json", fake_request_json)

    status = client.get("/api/webcams/node-auth-fail/status", headers=_auth_headers())
    assert status.status_code == 401
    assert status.json["error"]["code"] == "WEBCAM_UNAUTHORIZED"

    overview = client.get("/api/management/overview", headers=_auth_headers())
    assert overview.status_code == 200
    assert overview.json["webcams"][0]["error"]["code"] == "WEBCAM_UNAUTHORIZED"


def test_node_status_succeeds_when_upstream_token_is_accepted(monkeypatch, tmp_path):
    client, management_api = _new_management_client(monkeypatch, tmp_path)
    payload = {
        "id": "node-auth-ok",
        "name": "Auth OK Node",
        "base_url": "http://example.com",
        "auth": {"type": "bearer", "token": "shared-token"},
        "labels": {},
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "capabilities": ["stream"],
        "transport": "http",
    }
    created = client.post("/api/webcams", json=payload, headers=_auth_headers())
    assert created.status_code == 201

    def fake_request_json(node, method, path, body=None):
        assert path == "/api/status"
        return 200, {"status": "healthy", "stream_available": True}

    monkeypatch.setattr(management_api, "_request_json", fake_request_json)

    status = client.get("/api/webcams/node-auth-ok/status", headers=_auth_headers())
    assert status.status_code == 200
    assert status.json["stream_available"] is True
    assert status.json["status"] == "healthy"
    assert status.json["status_probe"]["status_code"] == 200


def test_node_status_returns_node_api_mismatch_when_status_endpoint_missing(monkeypatch, tmp_path):
    client, management_api = _new_management_client(monkeypatch, tmp_path)
    payload = {
        "id": "node-api-mismatch",
        "name": "API Mismatch Node",
        "base_url": "http://example.com",
        "auth": {"type": "none"},
        "labels": {},
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "capabilities": ["stream"],
        "transport": "http",
    }
    created = client.post("/api/webcams", json=payload, headers=_auth_headers())
    assert created.status_code == 201

    def fake_request_json(node, method, path, body=None):
        assert path == "/api/status"
        return 404, {"error": "missing"}

    monkeypatch.setattr(management_api, "_request_json", fake_request_json)

    status = client.get("/api/webcams/node-api-mismatch/status", headers=_auth_headers())
    assert status.status_code == 502
    assert status.json["error"]["code"] == "WEBCAM_API_MISMATCH"
    assert status.json["error"]["details"] == {
        "expected_endpoint": "/api/status",
        "received_status_code": 404,
    }


def test_node_status_maps_503_payload_without_error_envelope(monkeypatch, tmp_path):
    client, management_api = _new_management_client(monkeypatch, tmp_path)
    payload = {
        "id": "node-unhealthy",
        "name": "Unhealthy Node",
        "base_url": "http://example.com",
        "auth": {"type": "none"},
        "labels": {},
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "capabilities": ["stream"],
        "transport": "http",
    }
    created = client.post("/api/webcams", json=payload, headers=_auth_headers())
    assert created.status_code == 201

    def fake_request_json(node, method, path, body=None):
        assert path == "/api/status"
        return 503, {"status": "unhealthy", "stream_available": False}

    monkeypatch.setattr(management_api, "_request_json", fake_request_json)

    status = client.get("/api/webcams/node-unhealthy/status", headers=_auth_headers())
    assert status.status_code == 200
    assert status.json["webcam_id"] == "node-unhealthy"
    assert status.json["status"] == "unhealthy"
    assert status.json["stream_available"] is False

    overview = client.get("/api/management/overview", headers=_auth_headers())
    assert overview.status_code == 200
    assert overview.json["summary"]["unavailable_webcams"] == 0
    assert overview.json["summary"]["healthy_webcams"] == 0


def test_management_overview_counts_unsupported_transport_as_unavailable(monkeypatch, tmp_path):
    client, management_api = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "id": "node-non-http",
        "name": "Docker Node",
        "base_url": "docker://proxy:2375/container-id",
        "auth": {"type": "none"},
        "labels": {},
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "capabilities": ["stream"],
        "transport": "docker",
    }
    created = client.post("/api/webcams", json=payload, headers=_auth_headers())
    assert created.status_code == 201

    def fake_get_docker_container_status(proxy_host, proxy_port, container_id, auth_headers):
        raise management_api.NodeConnectivityError(
            "cannot connect",
            reason="connection refused",
            category="connection_refused_or_reset",
            raw_error="connection refused",
        )

    monkeypatch.setattr(
        management_api,
        "_get_docker_container_status",
        fake_get_docker_container_status,
    )

    overview = client.get("/api/management/overview", headers=_auth_headers())
    assert overview.status_code == 200
    assert overview.json["summary"]["total_webcams"] == 1
    assert overview.json["summary"]["unavailable_webcams"] == 1
    assert overview.json["summary"]["healthy_webcams"] == 0
    assert overview.json["webcams"][0]["error"]["code"] == "DOCKER_PROXY_UNREACHABLE"


def test_management_routes_require_authentication(monkeypatch, tmp_path):
    client, _ = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "id": "node-authz",
        "name": "Authz Node",
        "base_url": "http://example.com",
        "auth": {"type": "none"},
        "labels": {},
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "capabilities": ["stream"],
        "transport": "http",
    }

    created = client.post("/api/webcams", json=payload, headers=_auth_headers())
    assert created.status_code == 201

    endpoints = [
        ("get", "/api/webcams", None),
        ("post", "/api/webcams", payload),
        ("get", "/api/webcams/node-authz", None),
        ("put", "/api/webcams/node-authz", {"name": "renamed"}),
        ("delete", "/api/webcams/node-authz", None),
        ("get", "/api/webcams/node-authz/status", None),
        ("post", "/api/webcams/node-authz/actions/restart", {}),
        ("get", "/api/management/overview", None),
    ]

    for method, path, json_payload in endpoints:
        requester = getattr(client, method)
        kwargs = {"json": json_payload} if json_payload is not None else {}

        missing_token_response = requester(path, **kwargs)
        assert missing_token_response.status_code == 401
        assert missing_token_response.json["error"]["code"] == "UNAUTHORIZED"

        invalid_token_response = requester(
            path,
            headers={"Authorization": "Bearer invalid-token"},
            **kwargs,
        )
        assert invalid_token_response.status_code == 401
        assert invalid_token_response.json["error"]["code"] == "UNAUTHORIZED"


def test_node_status_maps_invalid_upstream_payload_to_controlled_error(monkeypatch, tmp_path):
    client, management_api = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "id": "node-invalid-status",
        "name": "Invalid Status Node",
        "base_url": "http://example.com",
        "auth": {"type": "none"},
        "labels": {},
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "capabilities": ["stream"],
        "transport": "http",
    }

    created = client.post("/api/webcams", json=payload, headers=_auth_headers())
    assert created.status_code == 201

    def raise_invalid_response(node, method, path, body=None):
        raise management_api.NodeInvalidResponseError("webcam returned malformed JSON")

    monkeypatch.setattr(management_api, "_request_json", raise_invalid_response)

    response = client.get("/api/webcams/node-invalid-status/status", headers=_auth_headers())
    assert response.status_code == 502
    assert response.json["error"]["code"] == "WEBCAM_INVALID_RESPONSE"
    assert response.json["error"]["details"]["reason"] == "malformed json"

    overview = client.get("/api/management/overview", headers=_auth_headers())
    assert overview.status_code == 200
    assert overview.json["webcams"][0]["error"]["code"] == "WEBCAM_INVALID_RESPONSE"


def test_node_action_forwards_restart_and_unsupported_action_payload(monkeypatch, tmp_path):
    client, management_api = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "id": "node-action-contract",
        "name": "Action Contract Node",
        "base_url": "http://example.com",
        "auth": {"type": "none"},
        "labels": {},
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "capabilities": ["stream"],
        "transport": "http",
    }

    created = client.post("/api/webcams", json=payload, headers=_auth_headers())
    assert created.status_code == 201

    def fake_request_json(node, method, path, body=None):
        assert node["id"] == "node-action-contract"
        assert method == "POST"
        if path == "/api/actions/restart":
            return 501, {
                "error": {
                    "code": "ACTION_NOT_IMPLEMENTED",
                    "message": "action 'restart' is recognized but not implemented",
                    "details": {"supported_actions": ["restart"]},
                }
            }
        if path == "/api/actions/refresh":
            return 400, {
                "error": {
                    "code": "ACTION_UNSUPPORTED",
                    "message": "action 'refresh' is not supported",
                    "details": {"supported_actions": ["restart"]},
                }
            }
        raise AssertionError(f"unexpected path: {path}")

    monkeypatch.setattr(management_api, "_request_json", fake_request_json)

    restart = client.post(
        "/api/webcams/node-action-contract/actions/restart",
        json={},
        headers=_auth_headers(),
    )
    assert restart.status_code == 501
    assert restart.json["action"] == "restart"
    assert restart.json["status_code"] == 501
    assert restart.json["response"]["error"]["code"] == "ACTION_NOT_IMPLEMENTED"

    unsupported = client.post(
        "/api/webcams/node-action-contract/actions/refresh",
        json={},
        headers=_auth_headers(),
    )
    assert unsupported.status_code == 400
    assert unsupported.json["action"] == "refresh"
    assert unsupported.json["status_code"] == 400
    assert unsupported.json["response"]["error"]["code"] == "ACTION_UNSUPPORTED"


def test_node_action_maps_invalid_upstream_payload_to_controlled_error(monkeypatch, tmp_path):
    client, management_api = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "id": "node-invalid-action",
        "name": "Invalid Action Node",
        "base_url": "http://example.com",
        "auth": {"type": "none"},
        "labels": {},
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "capabilities": ["stream"],
        "transport": "http",
    }

    created = client.post("/api/webcams", json=payload, headers=_auth_headers())
    assert created.status_code == 201

    def raise_invalid_response(node, method, path, body=None):
        raise management_api.NodeInvalidResponseError("webcam returned malformed JSON")

    monkeypatch.setattr(management_api, "_request_json", raise_invalid_response)

    response = client.post(
        "/api/webcams/node-invalid-action/actions/restart",
        json={},
        headers=_auth_headers(),
    )
    assert response.status_code == 502
    assert response.json["error"]["code"] == "WEBCAM_INVALID_RESPONSE"
    assert response.json["error"]["details"]["reason"] == "malformed json"
    assert response.json["error"]["details"]["action"] == "restart"




def test_node_status_maps_non_object_upstream_payload_to_controlled_error(monkeypatch, tmp_path):
    client, management_api = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "id": "node-non-object-status",
        "name": "Non Object Status Node",
        "base_url": "http://example.com",
        "auth": {"type": "none"},
        "labels": {},
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "capabilities": ["stream"],
        "transport": "http",
    }

    created = client.post("/api/webcams", json=payload, headers=_auth_headers())
    assert created.status_code == 201

    def raise_invalid_response(node, method, path, body=None):
        raise management_api.NodeInvalidResponseError("webcam returned non-object JSON")

    monkeypatch.setattr(management_api, "_request_json", raise_invalid_response)

    response = client.get("/api/webcams/node-non-object-status/status", headers=_auth_headers())
    assert response.status_code == 502
    assert response.json["error"]["code"] == "WEBCAM_INVALID_RESPONSE"
    assert response.json["error"]["details"]["reason"] == "malformed json"


def test_node_action_maps_non_object_upstream_payload_to_controlled_error(monkeypatch, tmp_path):
    client, management_api = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "id": "node-non-object-action",
        "name": "Non Object Action Node",
        "base_url": "http://example.com",
        "auth": {"type": "none"},
        "labels": {},
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "capabilities": ["stream"],
        "transport": "http",
    }

    created = client.post("/api/webcams", json=payload, headers=_auth_headers())
    assert created.status_code == 201

    def raise_invalid_response(node, method, path, body=None):
        raise management_api.NodeInvalidResponseError("webcam returned non-object JSON")

    monkeypatch.setattr(management_api, "_request_json", raise_invalid_response)

    response = client.post(
        "/api/webcams/node-non-object-action/actions/restart",
        json={},
        headers=_auth_headers(),
    )
    assert response.status_code == 502
    assert response.json["error"]["code"] == "WEBCAM_INVALID_RESPONSE"
    assert response.json["error"]["details"]["reason"] == "malformed json"
    assert response.json["error"]["details"]["action"] == "restart"

def test_create_node_migrates_legacy_auth_with_token(monkeypatch, tmp_path):
    client, _ = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "id": "node-legacy-convert",
        "name": "Legacy Convertible",
        "base_url": "http://example.com",
        "auth": {
            "type": "basic",
            "token": "api-token",
            "username": "legacy",
            "password": "legacy",
        },
        "labels": {},
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "capabilities": ["stream"],
        "transport": "http",
    }

    response = client.post("/api/webcams", json=payload, headers=_auth_headers())
    assert response.status_code == 201
    assert response.json["auth"] == {"type": "bearer", "token": "api-token"}


def test_request_json_uses_vetted_resolved_ip_and_preserves_host_header(monkeypatch):
    from pi_camera_in_docker import management_api

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"ok": true}'

    captured = {}

    def fake_getaddrinfo(host, port, proto):
        captured["getaddrinfo"] = (host, port, proto)
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 80)),
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 80)),
        ]

    class FakeHTTPConnection:
        def __init__(self, host, port, connect_host, timeout):
            captured["connect_host"] = connect_host
            captured["timeout"] = timeout
            _ = (host, port)

        def request(self, method, target, body=None, headers=None):
            captured["target"] = target
            captured["host"] = headers.get("Host")
            _ = (method, body)

        def getresponse(self):
            return FakeResponse()

        def close(self):
            return None

    monkeypatch.setattr(management_api.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(management_api, "_PinnedHTTPConnection", FakeHTTPConnection)

    status_code, payload = management_api._request_json(
        {"base_url": "http://example.com", "auth": {"type": "none"}},
        "GET",
        "/api/status",
    )

    assert status_code == 200
    assert payload == {"ok": True}
    assert captured["getaddrinfo"] == ("example.com", None, socket.IPPROTO_TCP)
    assert captured["connect_host"] == "93.184.216.34"
    assert captured["target"] == "/api/status"
    assert captured["host"] == "example.com"
    assert captured["timeout"] == management_api.REQUEST_TIMEOUT_SECONDS


def test_request_json_retries_next_vetted_address_when_first_connection_fails(monkeypatch):
    from pi_camera_in_docker import management_api

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"ok": true}'

    def fake_getaddrinfo(host, port, proto):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 80)),
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.35", 80)),
        ]

    attempted_addresses = []

    class FakeHTTPConnection:
        def __init__(self, host, port, connect_host, timeout):
            _ = (host, port, timeout)
            self.connect_host = connect_host

        def request(self, method, target, body=None, headers=None):
            _ = (method, target, body, headers)

        def getresponse(self):
            attempted_addresses.append(self.connect_host)
            if self.connect_host == "93.184.216.34":
                raise socket.timeout("timed out")
            return FakeResponse()

        def close(self):
            return None

    monkeypatch.setattr(management_api.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(management_api, "_PinnedHTTPConnection", FakeHTTPConnection)

    status_code, payload = management_api._request_json(
        {"base_url": "http://example.com", "auth": {"type": "none"}},
        "GET",
        "/api/status",
    )

    assert status_code == 200
    assert payload == {"ok": True}
    assert attempted_addresses == ["93.184.216.34", "93.184.216.35"]




def test_request_json_raises_for_array_json_payload(monkeypatch):
    from pi_camera_in_docker import management_api

    class FakeResponse:
        status = 200

        def read(self):
            return b"[1, 2, 3]"

    class FakeHTTPConnection:
        def __init__(self, host, port, connect_host, timeout):
            _ = (host, port, connect_host, timeout)

        def request(self, method, target, body=None, headers=None):
            _ = (method, target, body, headers)

        def getresponse(self):
            return FakeResponse()

        def close(self):
            return None

    monkeypatch.setattr(
        management_api.socket,
        "getaddrinfo",
        lambda host, port, proto: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 80))
        ],
    )
    monkeypatch.setattr(management_api, "_PinnedHTTPConnection", FakeHTTPConnection)

    with pytest.raises(management_api.NodeInvalidResponseError, match="non-object JSON"):
        management_api._request_json(
            {"base_url": "http://example.com", "auth": {"type": "none"}},
            "GET",
            "/api/status",
        )


def test_request_json_raises_for_scalar_json_payload(monkeypatch):
    from pi_camera_in_docker import management_api

    class FakeResponse:
        status = 200

        def read(self):
            return b'"ok"'

    class FakeHTTPConnection:
        def __init__(self, host, port, connect_host, timeout):
            _ = (host, port, connect_host, timeout)

        def request(self, method, target, body=None, headers=None):
            _ = (method, target, body, headers)

        def getresponse(self):
            return FakeResponse()

        def close(self):
            return None

    monkeypatch.setattr(
        management_api.socket,
        "getaddrinfo",
        lambda host, port, proto: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 80))
        ],
    )
    monkeypatch.setattr(management_api, "_PinnedHTTPConnection", FakeHTTPConnection)

    with pytest.raises(management_api.NodeInvalidResponseError, match="non-object JSON"):
        management_api._request_json(
            {"base_url": "http://example.com", "auth": {"type": "none"}},
            "GET",
            "/api/status",
        )

def test_request_json_maps_name_resolution_failure_to_dns_category(monkeypatch):
    from pi_camera_in_docker import management_api

    def fake_getaddrinfo(host, port, proto):
        raise socket.gaierror("name or service not known")

    monkeypatch.setattr(management_api.socket, "getaddrinfo", fake_getaddrinfo)

    webcam = {"base_url": "http://example.com", "auth": {"type": "none"}}
    try:
        management_api._request_json(webcam, "GET", "/api/status")
        raise AssertionError("expected NodeConnectivityError")
    except management_api.NodeConnectivityError as exc:
        assert exc.reason == "dns resolution failed"
        assert exc.category == "dns"


def test_vet_resolved_addresses_raises_when_all_addresses_blocked():
    from pi_camera_in_docker import management_api

    addresses = ("127.0.0.1", "10.0.0.5")

    try:
        management_api._vet_resolved_addresses(addresses)
        raise AssertionError("expected NodeRequestError")
    except management_api.NodeRequestError as exc:
        assert str(exc) == "webcam target is not allowed"


def test_vet_resolved_addresses_returns_only_allowed_from_mixed_results():
    from pi_camera_in_docker import management_api

    addresses = ("127.0.0.1", "93.184.216.34", "10.0.0.5", "93.184.216.35")

    assert management_api._vet_resolved_addresses(addresses) == ("93.184.216.34", "93.184.216.35")


def test_vet_resolved_addresses_deduplicates_allowed_addresses():
    from pi_camera_in_docker import management_api

    addresses = ("93.184.216.34", "93.184.216.34", "93.184.216.35", "93.184.216.35")

    assert management_api._vet_resolved_addresses(addresses) == ("93.184.216.34", "93.184.216.35")


def test_request_json_uses_allowed_ip_when_resolved_set_contains_blocked_ip(monkeypatch):
    from pi_camera_in_docker import management_api

    def fake_getaddrinfo(host, port, proto):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 80)),
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 80)),
        ]

    class FakeResponse:
        status = 200

        def read(self):
            return b'{"ok": true}'

    attempted_addresses = []

    class FakeHTTPConnection:
        def __init__(self, host, port, connect_host, timeout):
            _ = (host, port, timeout)
            self.connect_host = connect_host

        def request(self, method, target, body=None, headers=None):
            _ = (method, target, body, headers)

        def getresponse(self):
            attempted_addresses.append(self.connect_host)
            return FakeResponse()

        def close(self):
            return None

    monkeypatch.setattr(management_api.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(management_api, "_PinnedHTTPConnection", FakeHTTPConnection)

    webcam = {"base_url": "http://example.com", "auth": {"type": "none"}}
    status_code, payload = management_api._request_json(webcam, "GET", "/api/status")

    assert status_code == 200
    assert payload == {"ok": True}
    assert attempted_addresses == ["93.184.216.34"]


def test_request_json_maps_timeout_failure(monkeypatch):
    from pi_camera_in_docker import management_api

    captured = {}

    def fake_getaddrinfo(host, port, proto):
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 80))]

    class FakeHTTPConnection:
        def __init__(self, host, port, connect_host, timeout):
            captured["timeout"] = timeout
            _ = (host, port, connect_host)

        def request(self, method, target, body=None, headers=None):
            _ = (method, target, body, headers)

        def getresponse(self):
            raise socket.timeout("timed out")

        def close(self):
            return None

    monkeypatch.setattr(management_api.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(management_api, "_PinnedHTTPConnection", FakeHTTPConnection)

    webcam = {"base_url": "http://example.com", "auth": {"type": "none"}}
    try:
        management_api._request_json(webcam, "GET", "/api/status")
        raise AssertionError("expected NodeConnectivityError")
    except management_api.NodeConnectivityError as exc:
        assert captured["timeout"] == management_api.REQUEST_TIMEOUT_SECONDS
        assert exc.reason == "request timed out"
        assert exc.category == "timeout"


def test_request_json_maps_connection_refused_or_reset(monkeypatch):
    from pi_camera_in_docker import management_api

    def fake_getaddrinfo(host, port, proto):
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 80))]

    class FakeHTTPConnection:
        def __init__(self, host, port, connect_host, timeout):
            _ = (host, port, connect_host, timeout)

        def request(self, method, target, body=None, headers=None):
            _ = (method, target, body, headers)

        def getresponse(self):
            raise ConnectionRefusedError("connection refused")

        def close(self):
            return None

    monkeypatch.setattr(management_api.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(management_api, "_PinnedHTTPConnection", FakeHTTPConnection)

    webcam = {"base_url": "http://example.com", "auth": {"type": "none"}}
    try:
        management_api._request_json(webcam, "GET", "/api/status")
        raise AssertionError("expected NodeConnectivityError")
    except management_api.NodeConnectivityError as exc:
        assert exc.reason == "connection refused or reset"
        assert exc.category == "connection_refused_or_reset"


def test_request_json_maps_tls_failure(monkeypatch):
    from pi_camera_in_docker import management_api

    def fake_getaddrinfo(host, port, proto):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 443))
        ]

    class FakeHTTPSConnection:
        def __init__(self, host, port, connect_host, timeout, context):
            _ = (host, port, connect_host, timeout, context)

        def request(self, method, target, body=None, headers=None):
            _ = (method, target, body, headers)

        def getresponse(self):
            raise ssl.SSLError("certificate verify failed")

        def close(self):
            return None

    monkeypatch.setattr(management_api.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(management_api, "_PinnedHTTPSConnection", FakeHTTPSConnection)

    webcam = {"base_url": "https://example.com", "auth": {"type": "none"}}
    try:
        management_api._request_json(webcam, "GET", "/api/status")
        raise AssertionError("expected NodeConnectivityError")
    except management_api.NodeConnectivityError as exc:
        assert exc.reason == "tls handshake failed"
        assert exc.category == "tls"


def test_request_json_https_uses_hostname_for_tls_and_pins_vetted_ip(monkeypatch):
    from pi_camera_in_docker import management_api

    class FakeResponse:
        status = 200

        def read(self):
            return b'{"ok": true}'

    captured = {}

    def fake_getaddrinfo(host, port, proto):
        captured["getaddrinfo"] = (host, port, proto)
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 443))
        ]

    class FakeHTTPSConnection:
        def __init__(self, host, port, connect_host, timeout, context):
            captured["tls_host"] = host
            captured["connect_host"] = connect_host
            captured["timeout"] = timeout
            captured["has_context"] = context is not None
            _ = port

        def request(self, method, target, body=None, headers=None):
            captured["method"] = method
            captured["target"] = target
            captured["host_header"] = headers.get("Host")
            _ = body

        def getresponse(self):
            return FakeResponse()

        def close(self):
            return None

    monkeypatch.setattr(management_api.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(management_api, "_PinnedHTTPSConnection", FakeHTTPSConnection)

    status_code, payload = management_api._request_json(
        {"base_url": "https://example.com", "auth": {"type": "none"}},
        "GET",
        "/api/status",
    )

    assert status_code == 200
    assert payload == {"ok": True}
    assert captured["getaddrinfo"] == ("example.com", None, socket.IPPROTO_TCP)
    assert captured["tls_host"] == "example.com"
    assert captured["connect_host"] == "93.184.216.34"
    assert captured["method"] == "GET"
    assert captured["target"] == "/api/status"
    assert captured["host_header"] == "example.com"
    assert captured["timeout"] == management_api.REQUEST_TIMEOUT_SECONDS
    assert captured["has_context"] is True


def test_request_json_host_header_omits_userinfo_and_default_http_port(monkeypatch):
    from pi_camera_in_docker import management_api

    class FakeResponse:
        status = 200

        def read(self):
            return b'{"ok": true}'

    captured = {}

    def fake_getaddrinfo(host, port, proto):
        captured["getaddrinfo"] = (host, port, proto)
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 80))]

    class FakeHTTPConnection:
        def __init__(self, host, port, connect_host, timeout):
            _ = (host, port, connect_host, timeout)

        def request(self, method, target, body=None, headers=None):
            captured["host_header"] = headers.get("Host")
            _ = (method, target, body)

        def getresponse(self):
            return FakeResponse()

        def close(self):
            return None

    monkeypatch.setattr(management_api.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(management_api, "_PinnedHTTPConnection", FakeHTTPConnection)

    status_code, payload = management_api._request_json(
        {"base_url": "http://user:pass@example.com:80", "auth": {"type": "none"}},
        "GET",
        "/api/status",
    )

    assert status_code == 200
    assert payload == {"ok": True}
    assert captured["getaddrinfo"] == ("example.com", 80, socket.IPPROTO_TCP)
    assert captured["host_header"] == "example.com:80"


def test_request_json_host_header_formats_ipv6_and_omits_userinfo(monkeypatch):
    from pi_camera_in_docker import management_api

    ipv6_host = "2606:2800:220:1:248:1893:25c8:1946"

    class FakeResponse:
        status = 200

        def read(self):
            return b'{"ok": true}'

    captured = {}

    class FakeHTTPConnection:
        def __init__(self, host, port, connect_host, timeout):
            captured["connect"] = (host, port, connect_host, timeout)

        def request(self, method, target, body=None, headers=None):
            captured["host_header"] = headers.get("Host")
            _ = (method, target, body)

        def getresponse(self):
            return FakeResponse()

        def close(self):
            return None

    monkeypatch.setattr(
        management_api.socket,
        "getaddrinfo",
        lambda host, port, proto: [
            (
                socket.AF_INET6,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                (ipv6_host, 8443, 0, 0),
            )
        ],
    )
    monkeypatch.setattr(management_api, "_PinnedHTTPConnection", FakeHTTPConnection)

    status_code, payload = management_api._request_json(
        {"base_url": f"http://user:pass@[{ipv6_host}]:8443", "auth": {"type": "none"}},
        "GET",
        "/api/status",
    )

    assert status_code == 200
    assert payload == {"ok": True}
    assert captured["host_header"] == f"[{ipv6_host}]:8443"


def test_request_json_host_header_omits_default_https_port_without_explicit_port(monkeypatch):
    from pi_camera_in_docker import management_api

    class FakeResponse:
        status = 200

        def read(self):
            return b'{"ok": true}'

    captured = {}

    class FakeHTTPSConnection:
        def __init__(self, host, port, connect_host, timeout, context):
            _ = (host, port, connect_host, timeout, context)

        def request(self, method, target, body=None, headers=None):
            captured["host_header"] = headers.get("Host")
            _ = (method, target, body)

        def getresponse(self):
            return FakeResponse()

        def close(self):
            return None

    monkeypatch.setattr(
        management_api.socket,
        "getaddrinfo",
        lambda host, port, proto: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 443))
        ],
    )
    monkeypatch.setattr(management_api, "_PinnedHTTPSConnection", FakeHTTPSConnection)

    status_code, payload = management_api._request_json(
        {"base_url": "https://example.com", "auth": {"type": "none"}},
        "GET",
        "/api/status",
    )

    assert status_code == 200
    assert payload == {"ok": True}
    assert captured["host_header"] == "example.com"


def test_node_status_reports_connectivity_details(monkeypatch, tmp_path):
    client, management_api = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "id": "node-timeout",
        "name": "Timeout Node",
        "base_url": "http://example.com",
        "auth": {"type": "none"},
        "labels": {},
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "capabilities": ["stream"],
        "transport": "http",
    }
    created = client.post("/api/webcams", json=payload, headers=_auth_headers())
    assert created.status_code == 201

    def raise_timeout(node, method, path, body=None):
        raise management_api.NodeConnectivityError(
            "request timed out",
            reason="request timed out",
            category="timeout",
            raw_error="timed out while connecting to example.com:80\nwith extra spacing",
        )

    monkeypatch.setattr(management_api, "_request_json", raise_timeout)

    status = client.get("/api/webcams/node-timeout/status", headers=_auth_headers())
    assert status.status_code == 503
    assert status.json["error"]["code"] == "NETWORK_UNREACHABLE"
    assert status.json["error"]["details"]["reason"] == "request timed out"
    assert status.json["error"]["details"]["category"] == "timeout"
    assert "\n" not in status.json["error"]["details"]["raw_error"]


def test_webcam_api_status_contract_shape_reports_required_fields(monkeypatch):
    client = _new_webcam_contract_client()

    response = client.get("/api/status")

    assert response.status_code == 200
    payload = response.json
    assert payload["status"] in {"ok", "degraded"}
    assert payload["app_mode"] == "webcam"
    assert isinstance(payload["stream_available"], bool)
    assert isinstance(payload["camera_active"], bool)
    assert isinstance(payload["uptime_seconds"], float)
    assert isinstance(payload["fps"], (int, float))
    assert isinstance(payload["connections"], dict)
    assert sorted(payload["connections"].keys()) == ["current", "max"]
    assert isinstance(payload["connections"]["current"], int)
    assert isinstance(payload["connections"]["max"], int)
    assert isinstance(payload["timestamp"], str)


def test_webcam_api_status_contract_shape_with_auth(monkeypatch):
    client = _new_webcam_contract_client(auth_token="node-token")

    unauthorized = client.get("/api/status")
    assert unauthorized.status_code == 401
    assert unauthorized.json["error"]["code"] == "UNAUTHORIZED"

    authorized = client.get("/api/status", headers={"Authorization": "Bearer node-token"})
    assert authorized.status_code == 200
    assert authorized.json["app_mode"] == "webcam"


def test_node_action_passthrough_for_api_test_management_actions(monkeypatch, tmp_path):
    client, management_api = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "id": "node-api-test-actions",
        "name": "API Test Actions Node",
        "base_url": "http://example.com",
        "auth": {"type": "none"},
        "labels": {},
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "capabilities": ["stream"],
        "transport": "http",
    }

    created = client.post("/api/webcams", json=payload, headers=_auth_headers())
    assert created.status_code == 201

    captured_calls = []

    def fake_request_json(node, method, path, body=None):
        captured_calls.append((node["id"], method, path, body))
        if path == "/api/actions/api-test-start":
            return 200, {
                "ok": True,
                "action": "api-test-start",
                "api_test": {
                    "enabled": True,
                    "active": True,
                    "state_index": 0,
                    "state_name": "ok",
                    "next_transition_seconds": 1.0,
                },
            }
        if path == "/api/actions/api-test-step":
            return 200, {
                "ok": True,
                "action": "api-test-step",
                "api_test": {
                    "enabled": True,
                    "active": False,
                    "state_index": 1,
                    "state_name": "degraded",
                    "next_transition_seconds": None,
                },
            }
        if path == "/api/actions/api-test-stop":
            return 200, {
                "ok": True,
                "action": "api-test-stop",
                "api_test": {
                    "enabled": True,
                    "active": False,
                    "state_index": 1,
                    "state_name": "degraded",
                    "next_transition_seconds": None,
                },
            }
        if path == "/api/actions/api-test-reset":
            return 200, {
                "ok": True,
                "action": "api-test-reset",
                "api_test": {
                    "enabled": True,
                    "active": False,
                    "state_index": 0,
                    "state_name": "ok",
                    "next_transition_seconds": None,
                },
            }
        raise AssertionError(f"unexpected path: {path}")

    monkeypatch.setattr(management_api, "_request_json", fake_request_json)
    try:
        import main as main_module

        monkeypatch.setitem(
            main_module.register_management_routes.__globals__,
            "_request_json",
            fake_request_json,
        )
    except Exception:
        pass

    action_requests = [
        (
            "api-test-start",
            {"interval_seconds": 1, "scenario_order": [0, 1, 2]},
            {"enabled": True, "active": True, "state_index": 0},
        ),
        (
            "api-test-step",
            {},
            {"enabled": True, "active": False, "state_index": 1},
        ),
        (
            "api-test-stop",
            {},
            {"enabled": True, "active": False, "state_index": 1},
        ),
        (
            "api-test-reset",
            {},
            {"enabled": True, "active": False, "state_index": 0},
        ),
    ]

    for action_name, body, expected_api_test in action_requests:
        response = client.post(
            f"/api/webcams/node-api-test-actions/actions/{action_name}",
            json=body,
            headers=_auth_headers(),
        )
        assert response.status_code == 200
        assert response.json["webcam_id"] == "node-api-test-actions"
        assert response.json["action"] == action_name
        assert response.json["status_code"] == 200
        assert response.json["response"]["ok"] is True
        assert response.json["response"]["api_test"]["enabled"] == expected_api_test["enabled"]
        assert response.json["response"]["api_test"]["active"] == expected_api_test["active"]
        assert (
            response.json["response"]["api_test"]["state_index"] == expected_api_test["state_index"]
        )

    assert captured_calls == [
        (
            "node-api-test-actions",
            "POST",
            "/api/actions/api-test-start",
            {"interval_seconds": 1, "scenario_order": [0, 1, 2]},
        ),
        ("node-api-test-actions", "POST", "/api/actions/api-test-step", {}),
        ("node-api-test-actions", "POST", "/api/actions/api-test-stop", {}),
        ("node-api-test-actions", "POST", "/api/actions/api-test-reset", {}),
    ]


def test_diagnose_includes_structured_status_and_codes(monkeypatch):
    management_api = importlib.import_module("pi_camera_in_docker.management_api")

    webcam = {"id": "node-diag", "base_url": "http://example.invalid:8000", "transport": "http"}

    def _fake_getaddrinfo(*_args, **_kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 8000))]

    def _fake_request_json(*_args, **_kwargs):
        return 503, {"status": "degraded"}

    monkeypatch.setattr(management_api.socket, "getaddrinfo", _fake_getaddrinfo)
    monkeypatch.setattr(management_api, "_request_json", _fake_request_json)

    payload = management_api._diagnose_webcam(webcam)

    assert isinstance(payload["guidance"], list)
    assert isinstance(payload["recommendations"], list)
    assert payload["guidance"]
    assert payload["recommendations"]

    diagnostics = payload["diagnostics"]
    assert diagnostics["registration"]["status"] == "pass"
    assert diagnostics["url_validation"]["status"] == "pass"
    assert diagnostics["dns_resolution"]["status"] == "pass"
    assert diagnostics["network_connectivity"]["status"] == "pass"
    assert diagnostics["api_endpoint"]["status"] == "warn"
    assert diagnostics["api_endpoint"]["code"] == "API_STATUS_503"

    recommendation = payload["recommendations"][0]
    assert recommendation["status"] == "warn"
    assert recommendation["code"] == "API_STATUS_503"
    assert recommendation["message"] == payload["guidance"][0]


def test_diagnose_recommendations_reference_canonical_private_ip_variable(monkeypatch):
    monkeypatch.delenv("MIO_ALLOW_PRIVATE_IPS", raising=False)
    monkeypatch.delenv("MOTION_IN_OCEAN_ALLOW_PRIVATE_IPS", raising=False)

    management_api = importlib.import_module("pi_camera_in_docker.management_api")
    management_api = importlib.reload(management_api)

    webcam = {"id": "node-diag", "base_url": "http://example.invalid:8000", "transport": "http"}

    def _raise_timeout(*_args, **_kwargs):
        raise management_api.NodeConnectivityError(
            "timeout",
            reason="request timed out",
            category="timeout",
        )

    monkeypatch.setattr(
        management_api.socket, "getaddrinfo", lambda *_a, **_kw: [(2, 1, 6, "", ("8.8.8.8", 8000))]
    )
    monkeypatch.setattr(management_api, "_request_json", _raise_timeout)

    payload = management_api._diagnose_webcam(webcam)

    assert payload["guidance"] == [entry["message"] for entry in payload["recommendations"]]
    assert payload["recommendations"][0]["status"] == "fail"
    assert payload["recommendations"][0]["code"] == "NETWORK_CONNECTIVITY_ERROR"
    assert payload["diagnostics"]["network_connectivity"]["status"] == "fail"

    ssrf_webcam = {
        "id": "node-diag-ssrf",
        "base_url": "http://192.168.1.10:8000",
        "transport": "http",
    }
    ssrf_payload = management_api._diagnose_webcam(ssrf_webcam)
    ssrf_messages = [entry["message"] for entry in ssrf_payload["recommendations"]]
    assert any("MIO_ALLOW_PRIVATE_IPS=true" in message for message in ssrf_messages)
    assert all("MOTION_IN_OCEAN_ALLOW_PRIVATE_IPS" not in message for message in ssrf_messages)
