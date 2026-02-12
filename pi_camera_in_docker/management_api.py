import ipaddress
import json
import ssl
import socket
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse, urlunparse

from flask import Flask, jsonify, request
from node_registry import FileNodeRegistry, NodeValidationError


class NodeRequestError(RuntimeError):
    """Raised when a proxied node request cannot be completed safely."""


class NodeInvalidResponseError(NodeRequestError):
    """Raised when a proxied node responds with malformed JSON payload."""


class NodeConnectivityError(ConnectionError):
    """Raised when a proxied node request fails due to network-level connectivity issues."""

    def __init__(self, message: str, reason: str, category: str, raw_error: str = ""):
        super().__init__(message)
        self.reason = reason
        self.category = category
        self.raw_error = raw_error


#
# Docker Transport Support
# =======================
# This module supports two transport types for remote nodes:
#
# 1. "http" (HTTP/HTTPS) - Primary transport for most deployments
#    - Nodes communicate via HTTP requests to base_url + endpoints
#    - Simple setup, works across any network
#    - Status and actions fully supported
#
# 2. "docker" (Docker API via docker-socket-proxy) - Advanced transport
#    - Requires bearer token authentication and docker-socket-proxy setup on remote host
#    - Allows direct Docker API queries to remote hosts
#    - Status and actions not yet implemented (stub returns TRANSPORT_UNSUPPORTED)
#    - Use ENABLE_DOCKER_SOCKET_PROXY=true to activate docker-socket-proxy service
#    - See DEPLOYMENT.md for detailed setup instructions
#


def _extract_bearer_token() -> Optional[str]:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.lower().startswith("bearer "):
        return None
    token = auth_header[7:].strip()
    return token or None


def _validate_node_base_url(base_url: str) -> None:
    parsed = urlparse(base_url)
    hostname = parsed.hostname
    if parsed.scheme not in {"http", "https"} or not hostname:
        message = "node target is invalid"
        raise NodeRequestError(message)

    blocked_hosts = {"localhost", "metadata.google.internal", "metadata", "169.254.169.254"}
    if hostname.lower() in blocked_hosts:
        message = "node target is not allowed"
        raise NodeRequestError(message)


def _is_blocked_address(raw: str) -> bool:
    ip = ipaddress.ip_address(raw)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return any(
        (
            ip.is_private,
            ip.is_loopback,
            ip.is_link_local,
            ip.is_multicast,
            ip.is_reserved,
            ip.is_unspecified,
        )
    )


def _vet_resolved_addresses(addresses: Tuple[str, ...]) -> Tuple[str, ...]:
    vetted = []
    for address in addresses:
        if _is_blocked_address(address):
            message = "node target is not allowed"
            raise NodeRequestError(message)
        if address not in vetted:
            vetted.append(address)
    return tuple(vetted)


def _format_connect_netloc(address: str, port: Optional[int]) -> str:
    host = f"[{address}]" if ":" in address else address
    if port is None:
        return host
    return f"{host}:{port}"


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
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    }
    if node_id:
        payload["error"]["node_id"] = node_id
    return jsonify(payload), status_code


def _is_registry_corruption_error(exc: NodeValidationError) -> bool:
    return "node registry file is corrupted and cannot be parsed" in str(exc)


def _registry_corruption_response(exc: NodeValidationError):
    return _error_response(
        "REGISTRY_CORRUPTED",
        str(exc),
        500,
        details={"reason": "invalid registry json"},
    )


def _build_headers(node: Dict[str, Any]) -> Dict[str, str]:
    auth = node.get("auth", {})
    if auth.get("type") == "bearer" and auth.get("token"):
        return {"Authorization": f"Bearer {auth['token']}"}
    return {}


def _sanitize_error_text(raw_error: str, limit: int = 240) -> str:
    collapsed = " ".join(raw_error.split())
    if len(collapsed) <= limit:
        return collapsed
    return f"{collapsed[: limit - 3]}..."


def _classify_url_error(reason: Any) -> Tuple[str, str]:
    if isinstance(reason, (socket.timeout, TimeoutError)):
        return "request timed out", "timeout"
    if isinstance(reason, (ssl.SSLError, ssl.CertificateError)):
        return "tls handshake failed", "tls"
    if isinstance(reason, (ConnectionRefusedError, ConnectionResetError)):
        return "connection refused or reset", "connection_refused_or_reset"

    reason_text = str(reason).lower()
    if "timed out" in reason_text:
        return "request timed out", "timeout"
    if any(token in reason_text for token in ("certificate", "ssl", "tls", "wrong version number")):
        return "tls handshake failed", "tls"
    if any(token in reason_text for token in ("connection refused", "connection reset", "broken pipe")):
        return "connection refused or reset", "connection_refused_or_reset"
    return "connection failed", "network"


def _request_json(node: Dict[str, Any], method: str, path: str, body: Optional[dict] = None):
    base_url = node["base_url"].rstrip("/")
    _validate_node_base_url(base_url)

    url = base_url + path
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname
    if not hostname:
        message = "node target is invalid"
        raise NodeRequestError(message)

    port = parsed_url.port
    try:
        if _is_blocked_address(hostname):
            message = "node target is not allowed"
            raise NodeRequestError(message)
        resolved_addresses = (hostname,)
    except ValueError:
        try:
            records = socket.getaddrinfo(hostname, port or None, proto=socket.IPPROTO_TCP)
        except socket.gaierror as exc:
            raise NodeConnectivityError(
                "dns resolution failed",
                reason="dns resolution failed",
                category="dns",
                raw_error=str(exc),
            ) from exc
        resolved_addresses = tuple(record[4][0] for record in records)

    vetted_addresses = _vet_resolved_addresses(resolved_addresses)
    if not vetted_addresses:
        message = "name resolution returned no addresses"
        raise ConnectionError(message)

    headers = {"Content-Type": "application/json", **_build_headers(node)}
    headers.setdefault("Host", parsed_url.netloc)
    data = json.dumps(body).encode("utf-8") if body is not None else None

    connection_errors = []
    for address in vetted_addresses:
        connect_url = urlunparse(
            (
                parsed_url.scheme,
                _format_connect_netloc(address, port),
                parsed_url.path,
                parsed_url.params,
                parsed_url.query,
                parsed_url.fragment,
            )
        )

        try:
            req = urllib.request.Request(url=connect_url, method=method, headers=headers, data=data)
            with urllib.request.urlopen(req, timeout=2.5) as response:
                payload = response.read().decode("utf-8")
                if not payload:
                    return response.status, {}
                try:
                    return response.status, json.loads(payload)
                except json.JSONDecodeError as exc:
                    message = "node returned malformed JSON"
                    raise NodeInvalidResponseError(message) from exc
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode("utf-8") if exc.fp else ""
            try:
                body_json = json.loads(body_text) if body_text else {}
            except json.JSONDecodeError as decode_exc:
                message = "node returned malformed JSON"
                raise NodeInvalidResponseError(message) from decode_exc
            return exc.code, body_json
        except urllib.error.URLError as exc:
            reason, category = _classify_url_error(exc.reason)
            connection_errors.append(
                NodeConnectivityError(
                    reason,
                    reason=reason,
                    category=category,
                    raw_error=str(exc.reason),
                )
            )

    if connection_errors:
        if len(connection_errors) == 1:
            raise connection_errors[0]
        reason = "multiple connection failures"
        raw_error = "; ".join(err.raw_error for err in connection_errors if err.raw_error)
        raise NodeConnectivityError(
            reason,
            reason=reason,
            category="network",
            raw_error=raw_error,
        )

    raise ConnectionError("all connection attempts failed")


def _status_for_node(node: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[Tuple]]:
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
        status_code, status_payload = _request_json(node, "GET", "/api/status")
    except NodeInvalidResponseError:
        return {}, (
            "NODE_INVALID_RESPONSE",
            f"node {node_id} returned an invalid response",
            502,
            node_id,
            {"reason": "malformed json"},
        )
    except NodeRequestError:
        return {}, (
            "NODE_UNREACHABLE",
            f"node {node_id} is unreachable",
            503,
            node_id,
            {
                "reason": "target is blocked",
                "category": "blocked_target",
                "raw_error": "",
            },
        )
    except NodeConnectivityError as exc:
        return {}, (
            "NODE_UNREACHABLE",
            f"node {node_id} is unreachable",
            503,
            node_id,
            {
                "reason": exc.reason,
                "category": exc.category,
                "raw_error": _sanitize_error_text(exc.raw_error),
            },
        )
    except ConnectionError as exc:
        return {}, (
            "NODE_UNREACHABLE",
            f"node {node_id} is unreachable",
            503,
            node_id,
            {
                "reason": "connection failed",
                "category": "network",
                "raw_error": _sanitize_error_text(str(exc)),
            },
        )

    if status_code in {401, 403}:
        return {}, (
            "NODE_UNAUTHORIZED",
            f"node {node_id} rejected credentials",
            401,
            node_id,
            {"status_code": status_code},
        )

    if status_code == 404:
        return {}, (
            "NODE_API_MISMATCH",
            f"node {node_id} status probe endpoint was not found",
            502,
            node_id,
            {
                "expected_endpoint": "/api/status",
                "received_status_code": status_code,
            },
        )

    if status_code == 200:
        return {
            "node_id": node_id,
            "status": status_payload.get("status", "healthy"),
            "stream_available": bool(status_payload.get("stream_available", False)),
            "status_probe": {"status_code": status_code, "payload": status_payload},
        }, None

    if status_code == 503:
        return {
            "node_id": node_id,
            "status": status_payload.get("status", "unhealthy"),
            "stream_available": bool(status_payload.get("stream_available", False)),
            "status_probe": {"status_code": status_code, "payload": status_payload},
        }, None

    return {}, (
        "NODE_STATUS_ERROR",
        f"node {node_id} returned unexpected status response",
        502,
        node_id,
        {"status_code": status_code, "path": "/api/status"},
    )


def register_management_routes(
    app: Flask, registry_path: str, auth_token: str = ""
) -> None:
    registry = FileNodeRegistry(registry_path)

    def _enforce_management_auth() -> Optional[Tuple[Any, int]]:
        # Auth is required if and only if token is non-empty
        if not auth_token:
            return None
        token = _extract_bearer_token()
        if token is None or token != auth_token:
            return _error_response("UNAUTHORIZED", "authentication required", 401)
        return None

    @app.before_request
    def _management_auth_guard() -> Optional[Tuple[Any, int]]:
        if (
            request.path == "/api/management/overview"
            or request.path.startswith("/api/nodes/")
            or request.path == "/api/nodes"
        ):
            return _enforce_management_auth()
        return None

    @app.route("/api/nodes", methods=["GET"])
    def list_nodes():
        try:
            nodes = registry.list_nodes()
        except NodeValidationError as exc:
            if _is_registry_corruption_error(exc):
                return _registry_corruption_response(exc)
            raise
        return jsonify({"nodes": nodes}), 200

    @app.route("/api/nodes", methods=["POST"])
    def create_node():
        payload = request.get_json(silent=True) or {}
        try:
            created = registry.create_node(payload)
        except NodeValidationError as exc:
            if _is_registry_corruption_error(exc):
                return _registry_corruption_response(exc)
            return _error_response("VALIDATION_ERROR", str(exc), 400)
        return jsonify(created), 201

    @app.route("/api/nodes/<node_id>", methods=["GET"])
    def get_node(node_id: str):
        try:
            node = registry.get_node(node_id)
        except NodeValidationError as exc:
            if _is_registry_corruption_error(exc):
                return _registry_corruption_response(exc)
            raise
        if node is None:
            return _error_response(
                "NODE_NOT_FOUND", f"node {node_id} not found", 404, node_id=node_id
            )
        return jsonify(node), 200

    @app.route("/api/nodes/<node_id>", methods=["PUT"])
    def update_node(node_id: str):
        payload = request.get_json(silent=True) or {}

        try:
            existing = registry.get_node(node_id)
        except NodeValidationError as exc:
            if _is_registry_corruption_error(exc):
                return _registry_corruption_response(exc)
            raise
        effective_transport = payload.get(
            "transport",
            existing.get("transport") if (existing and isinstance(existing, dict)) else None,
        )
        try:
            updated = registry.update_node(node_id, payload)
        except KeyError:
            return _error_response(
                "NODE_NOT_FOUND", f"node {node_id} not found", 404, node_id=node_id
            )
        except NodeValidationError as exc:
            if _is_registry_corruption_error(exc):
                return _registry_corruption_response(exc)
            return _error_response("VALIDATION_ERROR", str(exc), 400, node_id=node_id)
        return jsonify(updated), 200

    @app.route("/api/nodes/<node_id>", methods=["DELETE"])
    def delete_node(node_id: str):
        try:
            deleted = registry.delete_node(node_id)
        except NodeValidationError as exc:
            if _is_registry_corruption_error(exc):
                return _registry_corruption_response(exc)
            raise
        if not deleted:
            return _error_response(
                "NODE_NOT_FOUND", f"node {node_id} not found", 404, node_id=node_id
            )
        return "", 204

    @app.route("/api/nodes/<node_id>/status", methods=["GET"])
    def node_status(node_id: str):
        try:
            node = registry.get_node(node_id)
        except NodeValidationError as exc:
            if _is_registry_corruption_error(exc):
                return _registry_corruption_response(exc)
            raise
        if node is None:
            return _error_response(
                "NODE_NOT_FOUND", f"node {node_id} not found", 404, node_id=node_id
            )

        result, error = _status_for_node(node)
        if error:
            return _error_response(*error)
        return jsonify(result), 200

    @app.route("/api/nodes/<node_id>/actions/<action>", methods=["POST"])
    def node_action(node_id: str, action: str):
        try:
            node = registry.get_node(node_id)
        except NodeValidationError as exc:
            if _is_registry_corruption_error(exc):
                return _registry_corruption_response(exc)
            raise
        if node is None:
            return _error_response(
                "NODE_NOT_FOUND", f"node {node_id} not found", 404, node_id=node_id
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
            status_code, response = _request_json(node, "POST", f"/api/actions/{action}", payload)
        except NodeInvalidResponseError:
            return _error_response(
                "NODE_INVALID_RESPONSE",
                f"node {node_id} returned an invalid response",
                502,
                node_id=node_id,
                details={"reason": "malformed json", "action": action},
            )
        except NodeRequestError:
            return _error_response(
                "NODE_UNREACHABLE",
                f"node {node_id} is unreachable",
                503,
                node_id=node_id,
                details={"reason": "target is blocked", "action": action},
            )
        except ConnectionError:
            return _error_response(
                "NODE_UNREACHABLE",
                f"node {node_id} is unreachable",
                503,
                node_id=node_id,
                details={"reason": "connection failed", "action": action},
            )

        if status_code in {401, 403}:
            return _error_response(
                "NODE_UNAUTHORIZED",
                f"node {node_id} rejected credentials",
                401,
                node_id=node_id,
                details={"action": action, "status_code": status_code},
            )
        return jsonify(
            {"node_id": node_id, "action": action, "status_code": status_code, "response": response}
        ), status_code

    @app.route("/api/management/overview", methods=["GET"])
    def management_overview():
        try:
            nodes = registry.list_nodes()
        except NodeValidationError as exc:
            if _is_registry_corruption_error(exc):
                return _registry_corruption_response(exc)
            raise
        statuses = []
        unavailable_nodes = 0
        for node in nodes:
            result, error = _status_for_node(node)
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
        healthy_nodes = sum(
            1
            for status in statuses
            if "error" not in status and str(status.get("status", "")).lower() in {"ok", "healthy", "ready"}
        )
        summary = {
            "total_nodes": len(nodes),
            "unavailable_nodes": unavailable_nodes,
            "healthy_nodes": healthy_nodes,
            "stream_available_nodes": stream_available_count,
        }
        return jsonify({"summary": summary, "nodes": statuses}), 200
