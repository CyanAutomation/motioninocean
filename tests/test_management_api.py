import importlib
import sys
from datetime import datetime


def _new_management_client(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_MODE", "management")
    monkeypatch.setenv("NODE_REGISTRY_PATH", str(tmp_path / "registry.json"))
    monkeypatch.setenv("MANAGEMENT_TOKEN_ROLES", "admin-token:admin,writer-token:write")
    sys.modules.pop("main", None)
    main = importlib.import_module("main")
    return main.create_management_app(main._load_config()).test_client()


def _auth_headers(token="admin-token"):
    return {"Authorization": f"Bearer {token}"}


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

    created = client.post("/api/nodes", json=payload, headers=_auth_headers())
    assert created.status_code == 201
    assert created.json["id"] == "node-1"

    listed = client.get("/api/nodes", headers=_auth_headers())
    assert listed.status_code == 200
    assert len(listed.json["nodes"]) == 1

    updated = client.put("/api/nodes/node-1", json={"name": "Front Door Cam"}, headers=_auth_headers())
    assert updated.status_code == 200
    assert updated.json["name"] == "Front Door Cam"

    status = client.get("/api/nodes/node-1/status", headers=_auth_headers())
    assert status.status_code == 503
    assert status.json["error"]["code"] == "NODE_UNREACHABLE"

    overview = client.get("/api/management/overview", headers=_auth_headers())
    assert overview.status_code == 200
    assert overview.json["summary"]["total_nodes"] == 1
    assert overview.json["summary"]["unavailable_nodes"] == 1

    deleted = client.delete("/api/nodes/node-1", headers=_auth_headers())
    assert deleted.status_code == 204


def test_validation_and_transport_errors(monkeypatch, tmp_path):
    monkeypatch.setenv("MANAGEMENT_TOKEN_ROLES", "admin-token:admin")
    client = _new_management_client(monkeypatch, tmp_path)

    invalid = client.post("/api/nodes", json={"id": "only-id"}, headers=_auth_headers())
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

    status = client.get("/api/nodes/node-2/status", headers=_auth_headers())
    assert status.status_code == 200
    assert status.json["error"]["code"] == "TRANSPORT_UNSUPPORTED"

    action = client.post("/api/nodes/node-2/actions/restart", json={}, headers=_auth_headers())
    assert action.status_code == 400
    assert action.json["error"]["code"] == "TRANSPORT_UNSUPPORTED"




def test_create_node_rejects_legacy_basic_auth(monkeypatch, tmp_path):
    client = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "id": "node-legacy-auth",
        "name": "Legacy Auth",
        "base_url": "http://example.com",
        "auth": {"type": "basic", "username": "camera", "password": "secret"},
        "labels": {},
        "last_seen": datetime.utcnow().isoformat(),
        "capabilities": ["stream"],
        "transport": "http",
    }

    response = client.post("/api/nodes", json=payload, headers=_auth_headers())
    assert response.status_code == 400
    assert response.json["error"]["code"] == "VALIDATION_ERROR"
    assert response.json["error"]["message"] == "auth.type must be one of: none, bearer"


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

    status = client.get("/api/nodes/node-3/status", headers=_auth_headers())
    assert status.status_code == 503
    assert status.json["error"]["code"] == "NODE_UNREACHABLE"
    assert status.json["error"]["details"]["reason"] == "target is blocked"


def test_corrupted_registry_file_recovers(monkeypatch, tmp_path):
    registry_path = tmp_path / "registry.json"
    registry_path.write_text("{invalid json", encoding="utf-8")

    monkeypatch.setenv("APP_MODE", "management")
    monkeypatch.setenv("NODE_REGISTRY_PATH", str(registry_path))
    monkeypatch.setenv("MANAGEMENT_TOKEN_ROLES", "admin-token:admin,writer-token:write")
    sys.modules.pop("main", None)
    main = importlib.import_module("main")
    client = main.create_management_app(main._load_config()).test_client()

    listed = client.get("/api/nodes", headers=_auth_headers())
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

    status = client.get("/api/nodes/node-4/status", headers=_auth_headers())
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

    status = client.get("/api/nodes/node-5/status", headers=_auth_headers())
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


def test_update_existing_docker_node_requires_admin_without_transport_in_payload(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("MANAGEMENT_AUTH_REQUIRED", "true")
    monkeypatch.setenv("MANAGEMENT_TOKEN_ROLES", "admin-token:admin,writer-token:write")
    client = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "id": "node-docker-update",
        "name": "Docker Update",
        "base_url": "http://docker.local",
        "auth": {"type": "none"},
        "labels": {},
        "last_seen": datetime.utcnow().isoformat(),
        "capabilities": ["stream"],
        "transport": "docker",
    }

    created = client.post(
        "/api/nodes",
        json=payload,
        headers={"Authorization": "Bearer admin-token"},
    )
    assert created.status_code == 201

    forbidden = client.put(
        "/api/nodes/node-docker-update",
        json={"name": "Updated Name"},
        headers={"Authorization": "Bearer writer-token"},
    )
    assert forbidden.status_code == 403
    assert forbidden.json["error"]["code"] == "FORBIDDEN"


def test_update_node_returns_404_when_node_disappears_during_update(monkeypatch, tmp_path):
    import management_api

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
        "last_seen": datetime.utcnow().isoformat(),
        "capabilities": ["stream"],
        "transport": "http",
    }

    created = client.post("/api/nodes", json=payload, headers=_auth_headers())
    assert created.status_code == 201

    response = client.put("/api/nodes/node-race", json={"name": "Updated Name"}, headers=_auth_headers())
    assert response.status_code == 404
    assert response.json["error"]["code"] == "NODE_NOT_FOUND"


def test_build_headers_for_bearer_auth_with_token():
    import management_api

    node = {"auth": {"type": "bearer", "token": "node-token"}}

    headers = management_api._build_headers(node)
    assert headers == {"Authorization": "Bearer node-token"}


def test_build_headers_for_bearer_auth_without_token_returns_empty_headers():
    import management_api

    node = {"auth": {"type": "bearer"}}

    headers = management_api._build_headers(node)
    assert headers == {}


def test_build_headers_for_non_bearer_auth_returns_empty_headers():
    import management_api

    node = {"auth": {"type": "basic", "encoded": "abc", "username": "camera", "password": "secret"}}

    headers = management_api._build_headers(node)
    assert headers == {}


def test_management_routes_require_authentication(monkeypatch, tmp_path):
    client = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "id": "node-authz",
        "name": "Authz Node",
        "base_url": "http://example.com",
        "auth": {"type": "none"},
        "labels": {},
        "last_seen": datetime.utcnow().isoformat(),
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
