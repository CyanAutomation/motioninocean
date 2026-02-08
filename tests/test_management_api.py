import importlib
import socket
import sys
from datetime import datetime, timezone


def _new_management_client(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_MODE", "management")
    monkeypatch.setenv("NODE_REGISTRY_PATH", str(tmp_path / "registry.json"))
    monkeypatch.setenv("MANAGEMENT_AUTH_TOKEN", "test-token")
    sys.modules.pop("main", None)
    main = importlib.import_module("main")
    return main.create_management_app(main._load_config()).test_client()


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

    status = client.get("/api/nodes/node-2/status", headers=_auth_headers())
    assert status.status_code == 200
    assert status.json["error"]["code"] == "TRANSPORT_UNSUPPORTED"

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
    assert "auth.type='basic' cannot be auto-migrated without an API token" in response.json["error"]["message"]


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
    assert status.json["error"]["code"] == "NODE_UNREACHABLE"
    assert status.json["error"]["details"]["reason"] == "target is blocked"


def test_corrupted_registry_file_returns_500_error_payload(monkeypatch, tmp_path):
    registry_path = tmp_path / "registry.json"
    registry_path.write_text("{invalid json", encoding="utf-8")

    monkeypatch.setenv("APP_MODE", "management")
    monkeypatch.setenv("NODE_REGISTRY_PATH", str(registry_path))
    monkeypatch.setenv("MANAGEMENT_AUTH_TOKEN", "test-token")
    sys.modules.pop("main", None)
    main = importlib.import_module("main")
    client = main.create_management_app(main._load_config()).test_client()

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
    assert status.json["error"]["code"] == "NODE_UNREACHABLE"
    assert status.json["error"]["details"]["reason"] == "target is blocked"


def test_docker_transport_allows_any_valid_token(monkeypatch, tmp_path):
    monkeypatch.setenv("MANAGEMENT_AUTH_REQUIRED", "true")
    client = _new_management_client(monkeypatch, tmp_path)

    payload = {
        "id": "node-docker-shared",
        "name": "Docker Shared Access",
        "base_url": "http://docker.local",
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
        "last_seen": datetime.now(timezone.utc).isoformat(),
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


def test_request_json_sends_bearer_auth_header_for_node_probes(monkeypatch):
    import management_api

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
    for path in ("/health", "/ready", "/metrics"):
        status_code, _ = management_api._request_json(node, "GET", path)
        assert status_code == 200

    assert captured["headers"] == ["Bearer node-token", "Bearer node-token", "Bearer node-token"]


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


def test_node_status_returns_node_unauthorized_when_upstream_rejects_token(monkeypatch, tmp_path):
    import management_api

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
        if path == "/health":
            return 401, {"status": "unauthorized"}
        return 200, {"status": "ready"}

    monkeypatch.setattr(management_api, "_request_json", fake_request_json)

    status = client.get("/api/nodes/node-auth-fail/status", headers=_auth_headers())
    assert status.status_code == 401
    assert status.json["error"]["code"] == "NODE_UNAUTHORIZED"

    overview = client.get("/api/management/overview", headers=_auth_headers())
    assert overview.status_code == 200
    assert overview.json["nodes"][0]["error"]["code"] == "NODE_UNAUTHORIZED"


def test_node_status_succeeds_when_upstream_token_is_accepted(monkeypatch, tmp_path):
    import management_api

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
        if path == "/health":
            return 200, {"status": "healthy"}
        if path == "/ready":
            return 200, {"status": "ready"}
        if path == "/metrics":
            return 200, {"frames_captured": 10, "current_fps": 5.0}
        raise AssertionError(f"unexpected path: {path}")

    monkeypatch.setattr(management_api, "_request_json", fake_request_json)

    status = client.get("/api/nodes/node-auth-ok/status", headers=_auth_headers())
    assert status.status_code == 200
    assert status.json["stream_available"] is True
    assert status.json["status"] == "healthy"


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
    import management_api

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


def test_node_action_maps_invalid_upstream_payload_to_controlled_error(monkeypatch, tmp_path):
    import management_api

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
    import management_api

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
        "/health",
    )

    assert status_code == 200
    assert payload == {"ok": True}
    assert captured["getaddrinfo"] == ("example.com", None, socket.IPPROTO_TCP)
    assert captured["url"] == "http://93.184.216.34/health"
    assert captured["host"] == "example.com"
    assert captured["timeout"] == 2.5




def test_request_json_maps_name_resolution_failure_to_node_request_error(monkeypatch):
    import management_api

    def fake_getaddrinfo(host, port, proto):
        raise socket.gaierror("name or service not known")

    monkeypatch.setattr(management_api.socket, "getaddrinfo", fake_getaddrinfo)

    node = {"base_url": "http://example.com", "auth": {"type": "none"}}
    try:
        management_api._request_json(node, "GET", "/health")
        raise AssertionError("expected NodeRequestError")
    except management_api.NodeRequestError as exc:
        assert str(exc) == "node target is invalid"

def test_request_json_rejects_blocked_ip_in_resolved_set(monkeypatch):
    import management_api

    def fake_getaddrinfo(host, port, proto):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 80)),
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 80)),
        ]

    monkeypatch.setattr(management_api.socket, "getaddrinfo", fake_getaddrinfo)

    node = {"base_url": "http://example.com", "auth": {"type": "none"}}
    try:
        management_api._request_json(node, "GET", "/health")
        raise AssertionError("expected NodeRequestError")
    except management_api.NodeRequestError as exc:
        assert str(exc) == "node target is not allowed"
