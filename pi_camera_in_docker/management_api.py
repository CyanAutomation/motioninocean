import json
import ipaddress
import urllib.error
import urllib.request
from datetime import datetime
from functools import wraps
from typing import Any, Dict, Optional, Set, Tuple
from urllib.parse import urlparse

from flask import Flask, jsonify, request

from node_registry import FileNodeRegistry, NodeValidationError


def _error_response(
    code: str,
    message: str,
    status_code: int,
    node_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
):
    payload: Dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat(),
        }
    }
    if node_id:
        payload["error"]["node_id"] = node_id
    return jsonify(payload), status_code


def _build_headers(node: Dict[str, Any]) -> Dict[str, str]:
    auth = node.get("auth", {})
    auth_type = auth.get("type", "none")
    if auth_type == "bearer" and auth.get("token"):
        return {"Authorization": f"Bearer {auth['token']}"}
    return {}


def _extract_api_token() -> str:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    return request.headers.get("X-API-Token", "").strip()


def _required_role_for_token(
    token: str, write_tokens: Set[str], admin_tokens: Set[str]
) -> Optional[str]:
    if token in admin_tokens:
        return "admin"
    if token in write_tokens:
        return "write"
    return None


def _validate_outbound_url(base_url: str, allowlist: Set[str]) -> None:
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("only http and https schemes are allowed")
    if not parsed.hostname:
        raise ValueError("base_url must include a hostname")

    hostname = parsed.hostname.lower()

    # Check IP literals first to block numeric loopback/private addresses.
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            raise ValueError(f"access to private IP ranges not allowed: {hostname}")
    except ValueError as exc:
        # Not an IP address, continue with hostname checks.
        if "does not appear to be" not in str(exc):
            raise

    # Block known metadata/restricted hostnames.
    if hostname in {"localhost", "metadata.google.internal", "169.254.169.254"}:
        raise ValueError(f"access to restricted host not allowed: {hostname}")

    if allowlist and hostname not in allowlist:
        raise ValueError(f"hostname {hostname} is not in MANAGEMENT_OUTBOUND_ALLOWLIST")


def _request_json(
    node: Dict[str, Any], method: str, path: str, allowlist: Set[str], body: Optional[dict] = None
):
    base_url = node["base_url"].rstrip("/")
    _validate_outbound_url(base_url, allowlist)

    url = base_url + path
    headers = {"Content-Type": "application/json", **_build_headers(node)}
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url=url, method=method, headers=headers, data=data)

    try:
        with urllib.request.urlopen(req, timeout=2.5) as response:  # noqa: S310
            payload = response.read().decode("utf-8")
            return response.status, json.loads(payload) if payload else {}
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8") if exc.fp else ""
        try:
            body_json = json.loads(body_text) if body_text else {}
        except json.JSONDecodeError:
            body_json = {"raw": body_text}
        return exc.code, body_json
    except urllib.error.URLError as exc:
        raise ConnectionError(str(exc.reason)) from exc


def _status_for_node(node: Dict[str, Any], allowlist: Set[str]) -> Tuple[Dict[str, Any], Optional[Tuple]]:
    node_id = node["id"]
    if node.get("transport") != "http":
        return {
            "node_id": node_id,
            "transport": node.get("transport"),
            "status": "unknown",
            "stream_available": False,
            "error": {
                "code": "TRANSPORT_UNSUPPORTED",
                "message": "status aggregation currently supports http transport only",
            },
        }, None

    try:
        health_code, health_payload = _request_json(node, "GET", "/health", allowlist)
        ready_code, ready_payload = _request_json(node, "GET", "/ready", allowlist)
        metrics_code, metrics_payload = _request_json(node, "GET", "/metrics", allowlist)
    except ValueError as exc:
        return {}, (
            "OUTBOUND_POLICY_VIOLATION",
            f"node {node_id} outbound request blocked",
            400,
            node_id,
            {"reason": "outbound URL failed policy validation"},
        )
    except ConnectionError as exc:
        return {}, (
            "NODE_UNREACHABLE",
            f"node {node_id} is unreachable",
            503,
            node_id,
            {"reason": str(exc)},
        )

    if any(code in {401, 403} for code in (health_code, ready_code, metrics_code)):
        return {}, (
            "NODE_UNAUTHORIZED",
            f"node {node_id} rejected credentials",
            401,
            node_id,
            {
                "health_code": health_code,
                "ready_code": ready_code,
                "metrics_code": metrics_code,
            },
        )

    status = {
        "node_id": node_id,
        "status": health_payload.get("status", "unknown"),
        "ready": ready_payload.get("status", "unknown"),
        "stream_available": ready_code == 200 and ready_payload.get("status") == "ready",
        "health": {"status_code": health_code, "payload": health_payload},
        "ready_probe": {"status_code": ready_code, "payload": ready_payload},
        "metrics": {"status_code": metrics_code, "payload": metrics_payload},
    }
    return status, None


def register_management_routes(app: Flask, config: Dict[str, Any]) -> None:
    registry = FileNodeRegistry(config["node_registry_path"])
    require_auth = config.get("management_auth_required", False)
    write_tokens = config.get("management_write_api_tokens", set())
    admin_tokens = config.get("management_admin_api_tokens", set())
    docker_socket_enabled = config.get("management_docker_socket_enabled", False)
    outbound_allowlist = config.get("management_outbound_allowlist", set())

    def require_role(min_role: str):
        def decorator(func):
            @wraps(func)
            def wrapped(*args, **kwargs):
                if not require_auth:
                    return func(*args, **kwargs)
                token = _extract_api_token()
                role = _required_role_for_token(token, write_tokens, admin_tokens)
                if role is None:
                    return _error_response(
                        "MANAGEMENT_AUTH_REQUIRED",
                        "valid management API token is required",
                        401,
                    )
                if min_role == "admin" and role != "admin":
                    return _error_response(
                        "MANAGEMENT_FORBIDDEN",
                        "admin role required for this operation",
                        403,
                    )
                return func(*args, **kwargs)

            return wrapped

        return decorator

    @app.route("/api/nodes", methods=["GET"])
    def list_nodes():
        return jsonify({"nodes": registry.list_nodes()}), 200

    @app.route("/api/nodes", methods=["POST"])
    @require_role("write")
    def create_node():
        payload = request.get_json(silent=True) or {}
        base_url = payload.get("base_url", "")
        if base_url:
            try:
                _validate_outbound_url(base_url, outbound_allowlist)
            except ValueError as exc:
                return _error_response(
                    "OUTBOUND_POLICY_VIOLATION",
                    "Outbound URL is not permitted by the current policy.",
                    400,
                )
        try:
            created = registry.create_node(payload)
        except NodeValidationError as exc:
            return _error_response(
                "VALIDATION_ERROR",
                "Request payload failed validation.",
                400,
            )
        return jsonify(created), 201

    @app.route("/api/nodes/<node_id>", methods=["GET"])
    def get_node(node_id: str):
        node = registry.get_node(node_id)
        if node is None:
            return _error_response("NODE_NOT_FOUND", f"node {node_id} not found", 404, node_id=node_id)
        return jsonify(node), 200

    @app.route("/api/nodes/<node_id>", methods=["PUT"])
    @require_role("write")
    def update_node(node_id: str):
        payload = request.get_json(silent=True) or {}
        base_url = payload.get("base_url")
        if isinstance(base_url, str):
            try:
                _validate_outbound_url(base_url, outbound_allowlist)
            except ValueError as exc:
                return _error_response(
                    "OUTBOUND_POLICY_VIOLATION",
                    "Outbound URL is not permitted by the current policy.",
                    400,
                    node_id=node_id,
                )
        try:
            updated = registry.update_node(node_id, payload)
        except NodeValidationError as exc:
            return _error_response(
                "VALIDATION_ERROR",
                "Request payload failed validation.",
                400,
                node_id=node_id,
            )
        except KeyError:
            return _error_response("NODE_NOT_FOUND", f"node {node_id} not found", 404, node_id=node_id)
        return jsonify(updated), 200

    @app.route("/api/nodes/<node_id>", methods=["DELETE"])
    @require_role("write")
    def delete_node(node_id: str):
        if not registry.delete_node(node_id):
            return _error_response("NODE_NOT_FOUND", f"node {node_id} not found", 404, node_id=node_id)
        return "", 204

    @app.route("/api/nodes/<node_id>/status", methods=["GET"])
    def node_status(node_id: str):
        node = registry.get_node(node_id)
        if node is None:
            return _error_response("NODE_NOT_FOUND", f"node {node_id} not found", 404, node_id=node_id)
        if node.get("transport") == "docker" and not docker_socket_enabled:
            return _error_response(
                "DOCKER_SOCKET_DISABLED",
                "docker transport is disabled; set MANAGEMENT_DOCKER_SOCKET_ENABLED=true to enable",
                403,
                node_id=node_id,
            )

        result, error = _status_for_node(node, outbound_allowlist)
        if error:
            return _error_response(*error)
        return jsonify(result), 200

    @app.route("/api/nodes/<node_id>/actions/<action>", methods=["POST"])
    @require_role("write")
    def node_action(node_id: str, action: str):
        node = registry.get_node(node_id)
        if node is None:
            return _error_response("NODE_NOT_FOUND", f"node {node_id} not found", 404, node_id=node_id)
        if node.get("transport") == "docker":
            token = _extract_api_token()
            role = _required_role_for_token(token, write_tokens, admin_tokens)
            if role != "admin":
                return _error_response(
                    "MANAGEMENT_FORBIDDEN",
                    "admin role required for docker operations",
                    403,
                    node_id=node_id,
                )
            if not docker_socket_enabled:
                return _error_response(
                    "DOCKER_SOCKET_DISABLED",
                    "docker transport is disabled; set MANAGEMENT_DOCKER_SOCKET_ENABLED=true to enable",
                    403,
                    node_id=node_id,
                )
            return _error_response(
                "DOCKER_OPERATION_UNAVAILABLE",
                "docker operations are not yet implemented",
                501,
                node_id=node_id,
            )

        if node.get("transport") != "http":
            return _error_response(
                "TRANSPORT_UNSUPPORTED",
                "actions currently support http transport only",
                400,
                node_id=node_id,
            )

        payload = request.get_json(silent=True) or {}
        try:
            status_code, response = _request_json(
                node, "POST", f"/api/actions/{action}", outbound_allowlist, payload
            )
        except ValueError as exc:
            return _error_response(
                "OUTBOUND_POLICY_VIOLATION",
                f"node {node_id} outbound request blocked",
                400,
                node_id=node_id,
                details={"reason": "outbound URL failed policy validation", "action": action},
            )
        except ConnectionError as exc:
            return _error_response(
                "NODE_UNREACHABLE",
                f"node {node_id} is unreachable",
                503,
                node_id=node_id,
                details={"reason": str(exc), "action": action},
            )

        if status_code in {401, 403}:
            return _error_response(
                "NODE_UNAUTHORIZED",
                f"node {node_id} rejected credentials",
                401,
                node_id=node_id,
                details={"action": action, "status_code": status_code},
            )
        return jsonify({"node_id": node_id, "action": action, "status_code": status_code, "response": response}), status_code

    @app.route("/api/management/overview", methods=["GET"])
    def management_overview():
        nodes = registry.list_nodes()
        statuses = []
        unavailable_nodes = 0
        for node in nodes:
            result, error = _status_for_node(node, outbound_allowlist)
            if error:
                unavailable_nodes += 1
                statuses.append(
                    {
                        "node_id": node["id"],
                        "status": "error",
                        "stream_available": False,
                        "error": {
                            "code": error[0],
                            "message": error[1],
                            "details": error[4],
                        },
                    }
                )
                continue
            statuses.append(result)

        stream_available_count = sum(1 for status in statuses if status.get("stream_available"))
        summary = {
            "total_nodes": len(nodes),
            "unavailable_nodes": unavailable_nodes,
            "stream_available_nodes": stream_available_count,
        }
        return jsonify({"summary": summary, "nodes": statuses}), 200
