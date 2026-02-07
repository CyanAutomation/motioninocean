import importlib
import sys
from datetime import datetime


def _new_management_client(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_MODE", "management")
    monkeypatch.setenv("NODE_REGISTRY_PATH", str(tmp_path / "registry.json"))
    sys.modules.pop("main", None)
    main = importlib.import_module("main")
    return main.create_management_app(main._load_config()).test_client()


def test_node_crud_and_overview(monkeypatch, tmp_path):
    client = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "id": "node-1",
        "name": "Front Door",
        "base_url": "http://nonexistent.invalid:65534",
        "auth": {"type": "none"},
        "labels": {"location": "entry"},
        "last_seen": datetime.utcnow().isoformat(),
        "capabilities": ["stream", "metrics"],
        "transport": "http",
    }

    created = client.post("/api/nodes", json=payload)
    assert created.status_code == 201
    assert created.json["id"] == "node-1"

    listed = client.get("/api/nodes")
    assert listed.status_code == 200
    assert len(listed.json["nodes"]) == 1

    updated = client.put("/api/nodes/node-1", json={"name": "Front Door Cam"})
    assert updated.status_code == 200
    assert updated.json["name"] == "Front Door Cam"

    status = client.get("/api/nodes/node-1/status")
    assert status.status_code in (401, 503)
    assert status.json["error"]["code"] in ("NODE_UNAUTHORIZED", "NODE_UNREACHABLE")

    overview = client.get("/api/management/overview")
    assert overview.status_code == 200
    assert overview.json["summary"]["total_nodes"] == 1
    assert overview.json["summary"]["unavailable_nodes"] == 1

    deleted = client.delete("/api/nodes/node-1")
    assert deleted.status_code == 204


def test_validation_and_transport_errors(monkeypatch, tmp_path):
    client = _new_management_client(monkeypatch, tmp_path)

    invalid = client.post("/api/nodes", json={"id": "only-id"})
    assert invalid.status_code == 400
    assert invalid.json["error"]["code"] == "VALIDATION_ERROR"

    payload = {
        "id": "node-2",
        "name": "Docker Node",
        "base_url": "http://docker.example.com",
        "auth": {"type": "none"},
        "labels": {},
        "last_seen": datetime.utcnow().isoformat(),
        "capabilities": ["stream"],
        "transport": "docker",
    }
    assert client.post("/api/nodes", json=payload).status_code == 201

    status = client.get("/api/nodes/node-2/status")
    assert status.status_code == 403
    assert status.json["error"]["code"] == "DOCKER_SOCKET_DISABLED"

    action = client.post("/api/nodes/node-2/actions/restart", json={})
    assert action.status_code == 403
    assert action.json["error"]["code"] == "MANAGEMENT_FORBIDDEN"


def test_management_write_auth_required(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_MODE", "management")
    monkeypatch.setenv("NODE_REGISTRY_PATH", str(tmp_path / "registry.json"))
    monkeypatch.setenv("MANAGEMENT_AUTH_REQUIRED", "true")
    monkeypatch.setenv("MANAGEMENT_WRITE_API_TOKENS", "write-token")
    monkeypatch.setenv("MANAGEMENT_ADMIN_API_TOKENS", "admin-token")
    sys.modules.pop("main", None)
    main = importlib.import_module("main")
    client = main.create_management_app(main._load_config()).test_client()

    payload = {
        "id": "node-auth",
        "name": "Protected",
        "base_url": "http://node.example.com",
        "auth": {"type": "none"},
        "labels": {},
        "last_seen": datetime.utcnow().isoformat(),
        "capabilities": ["stream"],
        "transport": "http",
    }
    denied = client.post("/api/nodes", json=payload)
    assert denied.status_code == 401
    assert denied.json["error"]["code"] == "MANAGEMENT_AUTH_REQUIRED"

    allowed = client.post(
        "/api/nodes", json=payload, headers={"Authorization": "Bearer write-token"}
    )
    assert allowed.status_code == 201


def test_outbound_allowlist_enforced(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_MODE", "management")
    monkeypatch.setenv("NODE_REGISTRY_PATH", str(tmp_path / "registry.json"))
    monkeypatch.setenv("MANAGEMENT_OUTBOUND_ALLOWLIST", "allowed.example.com")
    sys.modules.pop("main", None)
    main = importlib.import_module("main")
    client = main.create_management_app(main._load_config()).test_client()

    blocked = {
        "id": "node-blocked",
        "name": "Blocked",
        "base_url": "http://blocked.example.com",
        "auth": {"type": "none"},
        "labels": {},
        "last_seen": datetime.utcnow().isoformat(),
        "capabilities": ["stream"],
        "transport": "http",
    }
    response = client.post("/api/nodes", json=blocked)
    assert response.status_code == 400
    assert response.json["error"]["code"] == "OUTBOUND_POLICY_VIOLATION"


def test_docker_actions_require_admin_even_when_auth_disabled(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_MODE", "management")
    monkeypatch.setenv("NODE_REGISTRY_PATH", str(tmp_path / "registry.json"))
    monkeypatch.setenv("MANAGEMENT_AUTH_REQUIRED", "false")
    monkeypatch.setenv("MANAGEMENT_WRITE_API_TOKENS", "write-token")
    monkeypatch.setenv("MANAGEMENT_ADMIN_API_TOKENS", "admin-token")
    monkeypatch.setenv("MANAGEMENT_DOCKER_SOCKET_ENABLED", "true")
    sys.modules.pop("main", None)
    main = importlib.import_module("main")
    client = main.create_management_app(main._load_config()).test_client()

    payload = {
        "id": "docker-authz",
        "name": "Docker Node",
        "base_url": "http://docker.example.com",
        "auth": {"type": "none"},
        "labels": {},
        "last_seen": datetime.utcnow().isoformat(),
        "capabilities": ["stream"],
        "transport": "docker",
    }
    assert client.post("/api/nodes", json=payload).status_code == 201

    forbidden = client.post("/api/nodes/docker-authz/actions/restart", json={})
    assert forbidden.status_code == 403
    assert forbidden.json["error"]["code"] == "MANAGEMENT_FORBIDDEN"

    unavailable = client.post(
        "/api/nodes/docker-authz/actions/restart",
        json={},
        headers={"Authorization": "Bearer admin-token"},
    )
    assert unavailable.status_code == 501
    assert unavailable.json["error"]["code"] == "DOCKER_OPERATION_UNAVAILABLE"


def test_numeric_loopback_is_blocked(monkeypatch, tmp_path):
    client = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "id": "node-loopback",
        "name": "Loopback",
        "base_url": "http://127.0.0.1:8080",
        "auth": {"type": "none"},
        "labels": {},
        "last_seen": datetime.utcnow().isoformat(),
        "capabilities": ["stream"],
        "transport": "http",
    }

    response = client.post("/api/nodes", json=payload)
    assert response.status_code == 400
    assert response.json["error"]["code"] == "OUTBOUND_POLICY_VIOLATION"
