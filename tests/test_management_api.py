import importlib
import socket
import ssl
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask

from pi_camera_in_docker.application_settings import ApplicationSettings

# Import workspace root path (WORKSPACE_ROOT is set in conftest.py)
# For module-level imports
workspace_root = Path(__file__).parent.parent


def _new_management_client(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_MODE", "management")
    monkeypatch.setenv("NODE_REGISTRY_PATH", str(tmp_path / "registry.json"))
    monkeypatch.setenv("MANAGEMENT_AUTH_TOKEN", "test-token")
    # Monkeypatch ApplicationSettings to use tmp_path
    from pi_camera_in_docker.application_settings import ApplicationSettings
    original_app_settings_init = ApplicationSettings.__init__

    def mock_app_settings_init(self, path=None):
        if path is None:
            path = str(tmp_path / "application-settings.json")
        original_app_settings_init(self, path)

    monkeypatch.setattr(ApplicationSettings, "__init__", mock_app_settings_init)
    original_sys_path = sys.path.copy()
    sys.path.insert(0, str(workspace_root)) # Add the parent directory of pi_camera_in_docker to sys.path
    try:
        # Clear existing modules to ensure fresh import with new path
        sys.modules.pop("pi_camera_in_docker.main", None)
        sys.modules.pop("pi_camera_in_docker.management_api", None)
        # Import as a package module
        main = importlib.import_module("pi_camera_in_docker.main")
        return main.create_management_app(main._load_config()).test_client()
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


def _auth_headers(token="test-token"):
    return {"Authorization": f"Bearer {token}"}


def test_node_crud_and_overview(monkeypatch, tmp_path):
    client = _new_management_client(monkeypatch, tmp_path)

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

    created = client.post("/api/nodes", json=payload, headers=_auth_headers())
    assert created.status_code == 201
    assert created.json["id"] == "node-1"
    assert created.json["discovery"]["source"] == "manual"
    assert created.json["discovery"]["approved"] is True

    listed = client.get("/api/nodes", headers=_auth_headers())
    assert listed.status_code == 200
    assert len(listed.json["nodes"]) == 1

    updated = client.put(
        "/api/nodes/node-1", json={"name": "Front Door Cam"}, headers=_auth_headers()
    )
    assert updated.status_code == 200
    assert updated.json["name"] == "Front Door Cam"

    status = client.get("/api/nodes/node-1/status", headers=_auth_headers())
    assert status.status_code == 503
    assert status.json["error"]["code"] == "SSRF_BLOCKED"

    overview = client.get("/api/management/overview", headers=_auth_headers())
    assert overview.status_code == 200
    assert overview.json["summary"]["total_nodes"] == 1
    assert overview.json["summary"]["unavailable_nodes"] == 1
    assert overview.json["summary"]["healthy_nodes"] == 0

    deleted = client.delete("/api/nodes/node-1", headers=_auth_headers())
    assert deleted.status_code == 204


def test_validation_and_transport_errors(monkeypatch, tmp_path):
    client = _new_management_client(monkeypatch, tmp_path)

    invalid = client.post("/api/nodes", json={"id": "only-id"}, headers=_auth_headers())
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
            "/api/nodes",
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
    invalid_create = client.post("/api/nodes", json=invalid_docker_create, headers=_auth_headers())
    assert invalid_create.status_code == 400
    assert invalid_create.json["error"]["code"] == "VALIDATION_ERROR"
    assert "docker URL must include port" in invalid_create.json["error"]["message"]

    invalid_update = client.put(
        "/api/nodes/node-2",
        json={"base_url": "docker://proxy:2375"},
        headers=_auth_headers(),
    )
    assert invalid_update.status_code == 400
    assert invalid_update.json["error"]["code"] == "VALIDATION_ERROR"
    assert "docker URL must include container ID" in invalid_update.json["error"]["message"]

    action = client.post("/api/nodes/node-2/actions/restart", json={}, headers=_auth_headers())
    assert action.status_code == 400
    assert action.json["error"]["code"] == "TRANSPORT_UNSUPPORTED"


def test_create_node_rejects_unmigratable_legacy_basic_auth(monkeypatch, tmp_path):
    client = _new_management_client(monkeypatch, tmp_path)

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

    response = client.post("/api/nodes", json=payload, headers=_auth_headers())
    assert response.status_code == 400
    assert response.json["error"]["code"] == "VALIDATION_ERROR"
    assert (
        "auth.type='basic' cannot be auto-migrated without an API token"
        in response.json["error"]["message"]
    )


def test_ssrf_protection_blocks_local_targets(monkeypatch, tmp_path):
    client = _new_management_client(monkeypatch, tmp_path)

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
            "/api/nodes",
            json=payload,
            headers={"Authorization": "Bearer test-token"},
        ).status_code
        == 201
    )

    status = client.get("/api/nodes/node-3/status", headers=_auth_headers())
    assert status.status_code == 503
    assert status.json["error"]["code"] == "SSRF_BLOCKED"
    assert "SSRF protection" in status.json["error"]["details"]["reason"]
    assert status.json["error"]["details"]["category"] == "ssrf_blocked"


def test_corrupted_registry_file_returns_500_error_payload(monkeypatch, tmp_path):
    registry_path = tmp_path / "registry.json"
    registry_path.write_text("{invalid json", encoding="utf-8")

    monkeypatch.setenv("APP_MODE", "management")
    monkeypatch.setenv("NODE_REGISTRY_PATH", str(registry_path))
    monkeypatch.setenv("MANAGEMENT_AUTH_TOKEN", "test-token")
    original_sys_path = sys.path.copy()
    sys.path.insert(0, str(workspace_root)) # Add the parent directory of pi_camera_in_docker to sys.path
    try:
        sys.modules.pop("pi_camera_in_docker.main", None)
        sys.modules.pop("pi_camera_in_docker.management_api", None)
        main = importlib.import_module("pi_camera_in_docker.main")
        client = main.create_management_app(main._load_config()).test_client()
    finally:
        sys.path = original_sys_path

    listed = client.get("/api/nodes", headers=_auth_headers())
    assert listed.status_code == 500
    assert listed.json["error"]["code"] == "REGISTRY_CORRUPTED"
    assert listed.json["error"]["details"]["reason"] == "invalid registry json"

    overview = client.get("/api/management/overview", headers=_auth_headers())
    assert overview.status_code == 500
    assert overview.json["error"]["code"] == "REGISTRY_CORRUPTED"


def test_ssrf_protection_blocks_ipv6_mapped_loopback(monkeypatch, tmp_path):
    client = _new_management_client(monkeypatch, tmp_path)

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
            "/api/nodes",
            json=payload,
            headers={"Authorization": "Bearer test-token"},
        ).status_code
        == 201
    )

    status = client.get("/api/nodes/node-4/status", headers=_auth_headers())
    assert status.status_code == 503
    assert status.json["error"]["code"] == "SSRF_BLOCKED"
    assert "SSRF protection" in status.json["error"]["details"]["reason"]
    assert status.json["error"]["details"]["category"] == "ssrf_blocked"


def test_ssrf_protection_blocks_metadata_ip_literal(monkeypatch, tmp_path):
    client = _new_management_client(monkeypatch, tmp_path)

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
            "/api/nodes",
            json=payload,
            headers={"Authorization": "Bearer test-token"},
        ).status_code
        == 201
    )

    status = client.get("/api/nodes/node-5/status", headers=_auth_headers())
    assert status.status_code == 503
    assert status.json["error"]["code"] == "SSRF_BLOCKED"
    assert "SSRF protection" in status.json["error"]["details"]["reason"]
    assert status.json["error"]["details"]["category"] == "ssrf_blocked"


def test_docker_transport_allows_any_valid_token(monkeypatch, tmp_path):
    monkeypatch.setenv("MANAGEMENT_AUTH_REQUIRED", "true")
    client = _new_management_client(monkeypatch, tmp_path)

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

    unauthorized = client.post("/api/nodes", json=payload)
    assert unauthorized.status_code == 401
    assert unauthorized.json["error"]["code"] == "UNAUTHORIZED"

    invalid_token = client.post(
        "/api/nodes",
        json=payload,
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert invalid_token.status_code == 401
    assert invalid_token.json["error"]["code"] == "UNAUTHORIZED"

    authorized = client.post(
        "/api/nodes",
        json=payload,
        headers={"Authorization": "Bearer test-token"},
    )
    assert authorized.status_code == 201
    assert authorized.json["id"] == "node-docker-shared"


def test_update_node_returns_404_when_node_disappears_during_update(monkeypatch, tmp_path):
    import pi_camera_in_docker.management_api as management_api

    original_update_node = management_api.FileNodeRegistry.update_node

    def flaky_update_node(self, node_id, patch):
        if node_id == "node-race":
            raise KeyError(node_id)
        return original_update_node(self, node_id, patch)

    monkeypatch.setattr(management_api.FileNodeRegistry, "update_node", flaky_update_node)
    client = _new_management_client(monkeypatch, tmp_path)

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

    created = client.post("/api/nodes", json=payload, headers=_auth_headers())
    assert created.status_code == 201

    response = client.put(
        "/api/nodes/node-race", json={"name": "Updated Name"}, headers=_auth_headers()
    )
    assert response.status_code == 404
    assert response.json["error"]["code"] == "NODE_NOT_FOUND"


def test_discovery_announce_creates_then_updates_node(monkeypatch, tmp_path):
    monkeypatch.setenv("NODE_DISCOVERY_SHARED_SECRET", "discovery-secret")
    client = _new_management_client(monkeypatch, tmp_path)

    create_payload = {
        "node_id": "node-discovery-1",
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


def test_discovery_announce_parallel_requests_do_not_duplicate_error(monkeypatch, tmp_path):
    monkeypatch.setenv("NODE_DISCOVERY_SHARED_SECRET", "discovery-secret")
    client = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "node_id": "node-discovery-parallel",
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
    monkeypatch.setenv("NODE_DISCOVERY_SHARED_SECRET", "discovery-secret")
    client = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "node_id": "node-discovery-2",
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
    monkeypatch.setenv("NODE_DISCOVERY_SHARED_SECRET", "discovery-secret")
    monkeypatch.delenv("MOTION_IN_OCEAN_ALLOW_PRIVATE_IPS", raising=False)
    client = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "node_id": "node-discovery-private-blocked",
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
    assert (
        blocked.json["error"]["details"]["required_setting"]
        == "MOTION_IN_OCEAN_ALLOW_PRIVATE_IPS=true"
    )


def test_discovery_announce_allows_private_ip_with_opt_in(monkeypatch, tmp_path):
    monkeypatch.setenv("NODE_DISCOVERY_SHARED_SECRET", "discovery-secret")
    monkeypatch.setenv("MOTION_IN_OCEAN_ALLOW_PRIVATE_IPS", "true")
    client = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "node_id": "node-discovery-private-allowed",
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


def test_discovery_announce_validates_payload(monkeypatch, tmp_path):
    monkeypatch.setenv("NODE_DISCOVERY_SHARED_SECRET", "discovery-secret")
    client = _new_management_client(monkeypatch, tmp_path)

    invalid = client.post(
        "/api/discovery/announce",
        json={"node_id": "node-discovery-3"},
        headers={"Authorization": "Bearer discovery-secret"},
    )
    assert invalid.status_code == 400
    assert invalid.json["error"]["code"] == "VALIDATION_ERROR"


def test_discovery_approval_endpoint(monkeypatch, tmp_path):
    monkeypatch.setenv("NODE_DISCOVERY_SHARED_SECRET", "discovery-secret")
    client = _new_management_client(monkeypatch, tmp_path)

    announce_payload = {
        "node_id": "node-discovery-approval",
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
        "/api/nodes/node-discovery-approval/discovery/approve",
        headers=_auth_headers(),
    )
    assert approved.status_code == 200
    assert approved.json["node"]["discovery"]["approved"] is True

    rejected = client.post(
        "/api/nodes/node-discovery-approval/discovery/reject",
        headers=_auth_headers(),
    )
    assert rejected.status_code == 200
    assert rejected.json["node"]["discovery"]["approved"] is False


def test_build_headers_for_bearer_auth_with_token():
    import pi_camera_in_docker.management_api as management_api

    node = {"auth": {"type": "bearer", "token": "node-token"}}

    headers = management_api._build_headers(node)
    assert headers == {"Authorization": "Bearer node-token"}


def test_request_json_sends_bearer_auth_header_for_node_probes(monkeypatch):
    import pi_camera_in_docker.management_api as management_api

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

    def fake_urlopen(req, timeout):
        captured["headers"].append(req.get_header("Authorization"))
        return FakeResponse()

    monkeypatch.setattr(management_api.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(management_api.urllib.request, "urlopen", fake_urlopen)

    node = {"base_url": "http://example.com", "auth": {"type": "bearer", "token": "node-token"}}
    status_code, _ = management_api._request_json(node, "GET", "/api/status")
    assert status_code == 200

    assert captured["headers"] == ["Bearer node-token"]


def test_build_headers_for_bearer_auth_without_token_returns_empty_headers():
    import pi_camera_in_docker.management_api as management_api

    node = {"auth": {"type": "bearer"}}

    headers = management_api._build_headers(node)
    assert headers == {}


def test_build_headers_for_non_bearer_auth_returns_empty_headers():
    import pi_camera_in_docker.management_api as management_api

    node = {"auth": {"type": "basic", "encoded": "abc", "username": "camera", "password": "secret"}}

    headers = management_api._build_headers(node)
    assert headers == {}


def test_node_status_returns_node_unauthorized_when_upstream_rejects_token(monkeypatch, tmp_path):
    import pi_camera_in_docker.management_api as management_api

    client = _new_management_client(monkeypatch, tmp_path)
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
    created = client.post("/api/nodes", json=payload, headers=_auth_headers())
    assert created.status_code == 201

    def fake_request_json(node, method, path, body=None):
        assert path == "/api/status"
        return 401, {"status": "unauthorized"}

    monkeypatch.setattr(management_api, "_request_json", fake_request_json)

    status = client.get("/api/nodes/node-auth-fail/status", headers=_auth_headers())
    assert status.status_code == 401
    assert status.json["error"]["code"] == "NODE_UNAUTHORIZED"

    overview = client.get("/api/management/overview", headers=_auth_headers())
    assert overview.status_code == 200
    assert overview.json["nodes"][0]["error"]["code"] == "NODE_UNAUTHORIZED"


def test_node_status_succeeds_when_upstream_token_is_accepted(monkeypatch, tmp_path):
    import pi_camera_in_docker.management_api as management_api

    client = _new_management_client(monkeypatch, tmp_path)
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
    created = client.post("/api/nodes", json=payload, headers=_auth_headers())
    assert created.status_code == 201

    def fake_request_json(node, method, path, body=None):
        assert path == "/api/status"
        return 200, {"status": "healthy", "stream_available": True}

    monkeypatch.setattr(management_api, "_request_json", fake_request_json)

    status = client.get("/api/nodes/node-auth-ok/status", headers=_auth_headers())
    assert status.status_code == 200
    assert status.json["stream_available"] is True
    assert status.json["status"] == "healthy"
    assert status.json["status_probe"]["status_code"] == 200


def test_node_status_returns_node_api_mismatch_when_status_endpoint_missing(monkeypatch, tmp_path):
    import pi_camera_in_docker.management_api as management_api

    client = _new_management_client(monkeypatch, tmp_path)
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
    created = client.post("/api/nodes", json=payload, headers=_auth_headers())
    assert created.status_code == 201

    def fake_request_json(node, method, path, body=None):
        assert path == "/api/status"
        return 404, {"error": "missing"}

    monkeypatch.setattr(management_api, "_request_json", fake_request_json)

    status = client.get("/api/nodes/node-api-mismatch/status", headers=_auth_headers())
    assert status.status_code == 502
    assert status.json["error"]["code"] == "NODE_API_MISMATCH"
    assert status.json["error"]["details"] == {
        "expected_endpoint": "/api/status",
        "received_status_code": 404,
    }


def test_node_status_maps_503_payload_without_error_envelope(monkeypatch, tmp_path):
    import pi_camera_in_docker.management_api as management_api

    client = _new_management_client(monkeypatch, tmp_path)
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
    created = client.post("/api/nodes", json=payload, headers=_auth_headers())
    assert created.status_code == 201

    def fake_request_json(node, method, path, body=None):
        assert path == "/api/status"
        return 503, {"status": "unhealthy", "stream_available": False}

    monkeypatch.setattr(management_api, "_request_json", fake_request_json)

    status = client.get("/api/nodes/node-unhealthy/status", headers=_auth_headers())
    assert status.status_code == 200
    assert status.json["node_id"] == "node-unhealthy"
    assert status.json["status"] == "unhealthy"
    assert status.json["stream_available"] is False

    overview = client.get("/api/management/overview", headers=_auth_headers())
    assert overview.status_code == 200
    assert overview.json["summary"]["unavailable_nodes"] == 0
    assert overview.json["summary"]["healthy_nodes"] == 0


def test_management_routes_require_authentication(monkeypatch, tmp_path):
    client = _new_management_client(monkeypatch, tmp_path)

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

    created = client.post("/api/nodes", json=payload, headers=_auth_headers())
    assert created.status_code == 201

    endpoints = [
        ("get", "/api/nodes", None),
        ("post", "/api/nodes", payload),
        ("get", "/api/nodes/node-authz", None),
        ("put", "/api/nodes/node-authz", {"name": "renamed"}),
        ("delete", "/api/nodes/node-authz", None),
        ("get", "/api/nodes/node-authz/status", None),
        ("post", "/api/nodes/node-authz/actions/restart", {}),
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
    import pi_camera_in_docker.management_api as management_api

    client = _new_management_client(monkeypatch, tmp_path)

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

    created = client.post("/api/nodes", json=payload, headers=_auth_headers())
    assert created.status_code == 201

    def raise_invalid_response(node, method, path, body=None):
        raise management_api.NodeInvalidResponseError("node returned malformed JSON")

    monkeypatch.setattr(management_api, "_request_json", raise_invalid_response)

    response = client.get("/api/nodes/node-invalid-status/status", headers=_auth_headers())
    assert response.status_code == 502
    assert response.json["error"]["code"] == "NODE_INVALID_RESPONSE"
    assert response.json["error"]["details"]["reason"] == "malformed json"

    overview = client.get("/api/management/overview", headers=_auth_headers())
    assert overview.status_code == 200
    assert overview.json["nodes"][0]["error"]["code"] == "NODE_INVALID_RESPONSE"


def test_node_action_forwards_restart_and_unsupported_action_payload(monkeypatch, tmp_path):
    import pi_camera_in_docker.management_api as management_api

    client = _new_management_client(monkeypatch, tmp_path)

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

    created = client.post("/api/nodes", json=payload, headers=_auth_headers())
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
        "/api/nodes/node-action-contract/actions/restart",
        json={},
        headers=_auth_headers(),
    )
    assert restart.status_code == 501
    assert restart.json["action"] == "restart"
    assert restart.json["status_code"] == 501
    assert restart.json["response"]["error"]["code"] == "ACTION_NOT_IMPLEMENTED"

    unsupported = client.post(
        "/api/nodes/node-action-contract/actions/refresh",
        json={},
        headers=_auth_headers(),
    )
    assert unsupported.status_code == 400
    assert unsupported.json["action"] == "refresh"
    assert unsupported.json["status_code"] == 400
    assert unsupported.json["response"]["error"]["code"] == "ACTION_UNSUPPORTED"


def test_node_action_maps_invalid_upstream_payload_to_controlled_error(monkeypatch, tmp_path):
    import pi_camera_in_docker.management_api as management_api

    client = _new_management_client(monkeypatch, tmp_path)

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

    created = client.post("/api/nodes", json=payload, headers=_auth_headers())
    assert created.status_code == 201

    def raise_invalid_response(node, method, path, body=None):
        raise management_api.NodeInvalidResponseError("node returned malformed JSON")

    monkeypatch.setattr(management_api, "_request_json", raise_invalid_response)

    response = client.post(
        "/api/nodes/node-invalid-action/actions/restart",
        json={},
        headers=_auth_headers(),
    )
    assert response.status_code == 502
    assert response.json["error"]["code"] == "NODE_INVALID_RESPONSE"
    assert response.json["error"]["details"]["reason"] == "malformed json"
    assert response.json["error"]["details"]["action"] == "restart"


def test_create_node_migrates_legacy_auth_with_token(monkeypatch, tmp_path):
    client = _new_management_client(monkeypatch, tmp_path)

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

    response = client.post("/api/nodes", json=payload, headers=_auth_headers())
    assert response.status_code == 201
    assert response.json["auth"] == {"type": "bearer", "token": "api-token"}


def test_request_json_uses_vetted_resolved_ip_and_preserves_host_header(monkeypatch):
    import pi_camera_in_docker.management_api as management_api

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

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["host"] = req.get_header("Host")
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(management_api.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(management_api.urllib.request, "urlopen", fake_urlopen)

    status_code, payload = management_api._request_json(
        {"base_url": "http://example.com", "auth": {"type": "none"}},
        "GET",
        "/api/status",
    )

    assert status_code == 200
    assert payload == {"ok": True}
    assert captured["getaddrinfo"] == ("example.com", None, socket.IPPROTO_TCP)
    assert captured["url"] == "http://93.184.216.34/api/status"
    assert captured["host"] == "example.com"
    assert captured["timeout"] == management_api.REQUEST_TIMEOUT_SECONDS


def test_request_json_retries_next_vetted_address_when_first_connection_fails(monkeypatch):
    import pi_camera_in_docker.management_api as management_api

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

    attempted_urls = []

    def fake_urlopen(req, timeout):
        attempted_urls.append(req.full_url)
        if req.full_url == "http://93.184.216.34/api/status":
            raise management_api.urllib.error.URLError("timed out")
        return FakeResponse()

    monkeypatch.setattr(management_api.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(management_api.urllib.request, "urlopen", fake_urlopen)

    status_code, payload = management_api._request_json(
        {"base_url": "http://example.com", "auth": {"type": "none"}},
        "GET",
        "/api/status",
    )

    assert status_code == 200
    assert payload == {"ok": True}
    assert attempted_urls == [
        "http://93.184.216.34/api/status",
        "http://93.184.216.35/api/status",
    ]


def test_request_json_maps_name_resolution_failure_to_dns_category(monkeypatch):
    import pi_camera_in_docker.management_api as management_api

    def fake_getaddrinfo(host, port, proto):
        raise socket.gaierror("name or service not known")

    monkeypatch.setattr(management_api.socket, "getaddrinfo", fake_getaddrinfo)

    node = {"base_url": "http://example.com", "auth": {"type": "none"}}
    try:
        management_api._request_json(node, "GET", "/api/status")
        raise AssertionError("expected NodeConnectivityError")
    except management_api.NodeConnectivityError as exc:
        assert exc.reason == "dns resolution failed"
        assert exc.category == "dns"


def test_request_json_rejects_blocked_ip_in_resolved_set(monkeypatch):
    import pi_camera_in_docker.management_api as management_api

    def fake_getaddrinfo(host, port, proto):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 80)),
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 80)),
        ]

    monkeypatch.setattr(management_api.socket, "getaddrinfo", fake_getaddrinfo)

    node = {"base_url": "http://example.com", "auth": {"type": "none"}}
    try:
        management_api._request_json(node, "GET", "/api/status")
        raise AssertionError("expected NodeRequestError")
    except management_api.NodeRequestError as exc:
        assert str(exc) == "node target is not allowed"


def test_request_json_maps_timeout_failure(monkeypatch):
    import pi_camera_in_docker.management_api as management_api

    captured = {}

    def fake_getaddrinfo(host, port, proto):
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 80))]

    def fake_urlopen(req, timeout):
        captured["timeout"] = timeout
        raise management_api.urllib.error.URLError(socket.timeout("timed out"))

    monkeypatch.setattr(management_api.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(management_api.urllib.request, "urlopen", fake_urlopen)

    node = {"base_url": "http://example.com", "auth": {"type": "none"}}
    try:
        management_api._request_json(node, "GET", "/api/status")
        raise AssertionError("expected NodeConnectivityError")
    except management_api.NodeConnectivityError as exc:
        assert captured["timeout"] == management_api.REQUEST_TIMEOUT_SECONDS
        assert exc.reason == "request timed out"
        assert exc.category == "timeout"


def test_request_json_maps_connection_refused_or_reset(monkeypatch):
    import pi_camera_in_docker.management_api as management_api

    def fake_getaddrinfo(host, port, proto):
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 80))]

    def fake_urlopen(req, timeout):
        raise management_api.urllib.error.URLError(ConnectionRefusedError("connection refused"))

    monkeypatch.setattr(management_api.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(management_api.urllib.request, "urlopen", fake_urlopen)

    node = {"base_url": "http://example.com", "auth": {"type": "none"}}
    try:
        management_api._request_json(node, "GET", "/api/status")
        raise AssertionError("expected NodeConnectivityError")
    except management_api.NodeConnectivityError as exc:
        assert exc.reason == "connection refused or reset"
        assert exc.category == "connection_refused_or_reset"


def test_request_json_maps_tls_failure(monkeypatch):
    import pi_camera_in_docker.management_api as management_api

    def fake_getaddrinfo(host, port, proto):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 443))
        ]

    def fake_urlopen(req, timeout):
        raise management_api.urllib.error.URLError(ssl.SSLError("certificate verify failed"))

    monkeypatch.setattr(management_api.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(management_api.urllib.request, "urlopen", fake_urlopen)

    node = {"base_url": "https://example.com", "auth": {"type": "none"}}
    try:
        management_api._request_json(node, "GET", "/api/status")
        raise AssertionError("expected NodeConnectivityError")
    except management_api.NodeConnectivityError as exc:
        assert exc.reason == "tls handshake failed"
        assert exc.category == "tls"


def test_node_status_reports_connectivity_details(monkeypatch, tmp_path):
    import pi_camera_in_docker.management_api as management_api

    client = _new_management_client(monkeypatch, tmp_path)

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
    created = client.post("/api/nodes", json=payload, headers=_auth_headers())
    assert created.status_code == 201

    def raise_timeout(node, method, path, body=None):
        raise management_api.NodeConnectivityError(
            "request timed out",
            reason="request timed out",
            category="timeout",
            raw_error="timed out while connecting to example.com:80\nwith extra spacing",
        )

    monkeypatch.setattr(management_api, "_request_json", raise_timeout)

    status = client.get("/api/nodes/node-timeout/status", headers=_auth_headers())
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
    import pi_camera_in_docker.management_api as management_api

    client = _new_management_client(monkeypatch, tmp_path)

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

    created = client.post("/api/nodes", json=payload, headers=_auth_headers())
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
            f"/api/nodes/node-api-test-actions/actions/{action_name}",
            json=body,
            headers=_auth_headers(),
        )
        assert response.status_code == 200
        assert response.json["node_id"] == "node-api-test-actions"
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

    node = {"id": "node-diag", "base_url": "http://example.invalid:8000", "transport": "http"}

    def _fake_getaddrinfo(*_args, **_kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 8000))]

    def _fake_request_json(*_args, **_kwargs):
        return 503, {"status": "degraded"}

    monkeypatch.setattr(management_api.socket, "getaddrinfo", _fake_getaddrinfo)
    monkeypatch.setattr(management_api, "_request_json", _fake_request_json)

    payload = management_api._diagnose_node(node)

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


def test_diagnose_recommendations_keep_backward_compatible_guidance(monkeypatch):
    management_api = importlib.import_module("management_api")

    node = {"id": "node-diag", "base_url": "http://example.invalid:8000", "transport": "http"}

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

    payload = management_api._diagnose_node(node)

    assert payload["guidance"] == [entry["message"] for entry in payload["recommendations"]]
    assert payload["recommendations"][0]["status"] == "fail"
    assert payload["recommendations"][0]["code"] == "NETWORK_CONNECTIVITY_ERROR"
    assert payload["diagnostics"]["network_connectivity"]["status"] == "fail"
