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
        "base_url": "http://127.0.0.1:65534",
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
    assert status.status_code == 503
    assert status.json["error"]["code"] == "NODE_UNREACHABLE"

    overview = client.get("/api/management/overview")
    assert overview.status_code == 200
    assert overview.json["summary"]["total_nodes"] == 1
    assert overview.json["summary"]["unavailable_nodes"] == 1

    deleted = client.delete("/api/nodes/node-1")
    assert deleted.status_code == 204


def test_validation_and_transport_errors(monkeypatch, tmp_path):
    monkeypatch.setenv("MANAGEMENT_TOKEN_ROLES", "admin-token:admin")
    client = _new_management_client(monkeypatch, tmp_path)

    invalid = client.post("/api/nodes", json={"id": "only-id"})
    assert invalid.status_code == 400
    assert invalid.json["error"]["code"] == "VALIDATION_ERROR"

    payload = {
        "id": "node-2",
        "name": "Docker Node",
        "base_url": "http://docker.local",
        "auth": {"type": "none"},
        "labels": {},
        "last_seen": datetime.utcnow().isoformat(),
        "capabilities": ["stream"],
        "transport": "docker",
    }
    assert (
        client.post(
            "/api/nodes",
            json=payload,
            headers={"Authorization": "Bearer admin-token"},
        ).status_code
        == 201
    )

    status = client.get("/api/nodes/node-2/status")
    assert status.status_code == 200
    assert status.json["error"]["code"] == "TRANSPORT_UNSUPPORTED"

    action = client.post("/api/nodes/node-2/actions/restart", json={})
    assert action.status_code == 400
    assert action.json["error"]["code"] == "TRANSPORT_UNSUPPORTED"


def test_ssrf_protection_blocks_local_targets(monkeypatch, tmp_path):
    client = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "id": "node-3",
        "name": "Internal Node",
        "base_url": "http://127.0.0.1:8080",
        "auth": {"type": "none"},
        "labels": {},
        "last_seen": datetime.utcnow().isoformat(),
        "capabilities": ["metrics"],
        "transport": "http",
    }
    assert (
        client.post(
            "/api/nodes",
            json=payload,
            headers={"Authorization": "Bearer admin-token"},
        ).status_code
        == 201
    )

    status = client.get("/api/nodes/node-3/status")
    assert status.status_code == 503
    assert status.json["error"]["code"] == "NODE_UNREACHABLE"
    assert status.json["error"]["details"]["reason"] == "target is blocked"


def test_corrupted_registry_file_recovers(monkeypatch, tmp_path):
    registry_path = tmp_path / "registry.json"
    registry_path.write_text("{invalid json", encoding="utf-8")

    monkeypatch.setenv("APP_MODE", "management")
    monkeypatch.setenv("NODE_REGISTRY_PATH", str(registry_path))
    sys.modules.pop("main", None)
    main = importlib.import_module("main")
    client = main.create_management_app(main._load_config()).test_client()

    listed = client.get("/api/nodes")
    assert listed.status_code == 200
    assert listed.json == {"nodes": []}


def test_ssrf_protection_blocks_ipv6_mapped_loopback(monkeypatch, tmp_path):
    client = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "id": "node-4",
        "name": "Mapped Loopback",
        "base_url": "http://[::ffff:127.0.0.1]:8080",
        "auth": {"type": "none"},
        "labels": {},
        "last_seen": datetime.utcnow().isoformat(),
        "capabilities": ["metrics"],
        "transport": "http",
    }
    assert (
        client.post(
            "/api/nodes",
            json=payload,
            headers={"Authorization": "Bearer admin-token"},
        ).status_code
        == 201
    )

    status = client.get("/api/nodes/node-4/status")
    assert status.status_code == 503
    assert status.json["error"]["code"] == "NODE_UNREACHABLE"
    assert status.json["error"]["details"]["reason"] == "target is blocked"


def test_ssrf_protection_blocks_metadata_ip_literal(monkeypatch, tmp_path):
    client = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "id": "node-5",
        "name": "Metadata Target",
        "base_url": "http://169.254.169.254",
        "auth": {"type": "none"},
        "labels": {},
        "last_seen": datetime.utcnow().isoformat(),
        "capabilities": ["metrics"],
        "transport": "http",
    }
    assert (
        client.post(
            "/api/nodes",
            json=payload,
            headers={"Authorization": "Bearer admin-token"},
        ).status_code
        == 201
    )

    status = client.get("/api/nodes/node-5/status")
    assert status.status_code == 503
    assert status.json["error"]["code"] == "NODE_UNREACHABLE"
    assert status.json["error"]["details"]["reason"] == "target is blocked"


def test_docker_transport_requires_admin_when_auth_disabled(monkeypatch, tmp_path):
    monkeypatch.setenv("MANAGEMENT_AUTH_REQUIRED", "false")
    monkeypatch.setenv("MANAGEMENT_TOKEN_ROLES", "admin-token:admin")
    client = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "id": "node-docker-no-auth",
        "name": "Docker No Auth",
        "base_url": "http://docker.local",
        "auth": {"type": "none"},
        "labels": {},
        "last_seen": datetime.utcnow().isoformat(),
        "capabilities": ["stream"],
        "transport": "docker",
    }

    forbidden = client.post("/api/nodes", json=payload)
    assert forbidden.status_code == 403
    assert forbidden.json["error"]["code"] == "FORBIDDEN"


def test_docker_transport_allows_admin_token(monkeypatch, tmp_path):
    monkeypatch.setenv("MANAGEMENT_AUTH_REQUIRED", "true")
    monkeypatch.setenv("MANAGEMENT_TOKEN_ROLES", "admin-token:admin,writer-token:write")
    client = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "id": "node-docker-admin",
        "name": "Docker Admin",
        "base_url": "http://docker.local",
        "auth": {"type": "none"},
        "labels": {},
        "last_seen": datetime.utcnow().isoformat(),
        "capabilities": ["stream"],
        "transport": "docker",
    }

    unauthorized = client.post("/api/nodes", json=payload)
    assert unauthorized.status_code == 401
    assert unauthorized.json["error"]["code"] == "UNAUTHORIZED"

    non_admin = client.post(
        "/api/nodes",
        json=payload,
        headers={"Authorization": "Bearer writer-token"},
    )
    assert non_admin.status_code == 403
    assert non_admin.json["error"]["code"] == "FORBIDDEN"

    authorized = client.post(
        "/api/nodes",
        json=payload,
        headers={"Authorization": "Bearer admin-token"},
    )
    assert authorized.status_code == 201
    assert authorized.json["id"] == "node-docker-admin"
