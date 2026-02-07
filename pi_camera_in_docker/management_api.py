import json
import socket
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

from flask import Flask, jsonify, request

from node_registry import FileNodeRegistry, NodeValidationError


class NodeRequestError(RuntimeError):
    """Raised when a proxied node request cannot be completed safely."""


def _validate_node_base_url(base_url: str) -> None:
    import ipaddress

    parsed = urlparse(base_url)
    hostname = parsed.hostname
    if parsed.scheme not in {"http", "https"} or not hostname:
        raise NodeRequestError("node target is invalid")

    blocked_hosts = {"localhost", "metadata.google.internal", "metadata"}
    if hostname.lower() in blocked_hosts:
        raise NodeRequestError("node target is not allowed")

    def _is_blocked_address(raw: str) -> bool:
        ip = ipaddress.ip_address(raw)
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

    try:
        if _is_blocked_address(hostname):
            raise NodeRequestError("node target is not allowed")
    except ValueError:
        try:
            records = socket.getaddrinfo(hostname, parsed.port or None, proto=socket.IPPROTO_TCP)
        except socket.gaierror:
            return

        for record in records:
            resolved_ip = record[4][0]
            if _is_blocked_address(resolved_ip):
                raise NodeRequestError("node target is not allowed")


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


def _request_json(node: Dict[str, Any], method: str, path: str, body: Optional[dict] = None):
    base_url = node["base_url"].rstrip("/")
    _validate_node_base_url(base_url)

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
        health_code, health_payload = _request_json(node, "GET", "/health")
        ready_code, ready_payload = _request_json(node, "GET", "/ready")
        metrics_code, metrics_payload = _request_json(node, "GET", "/metrics")
    except NodeRequestError:
        return {}, (
            "NODE_UNREACHABLE",
            f"node {node_id} is unreachable",
            503,
            node_id,
            {"reason": "target is blocked"},
        )
    except ConnectionError:
        return {}, (
            "NODE_UNREACHABLE",
            f"node {node_id} is unreachable",
            503,
            node_id,
            {"reason": "connection failed"},
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


def register_management_routes(app: Flask, registry_path: str) -> None:
    registry = FileNodeRegistry(registry_path)

    @app.route("/api/nodes", methods=["GET"])
    def list_nodes():
        return jsonify({"nodes": registry.list_nodes()}), 200

    @app.route("/api/nodes", methods=["POST"])
    def create_node():
        payload = request.get_json(silent=True) or {}
        try:
            created = registry.create_node(payload)
        except NodeValidationError as exc:
            return _error_response("VALIDATION_ERROR", str(exc), 400)
        return jsonify(created), 201

    @app.route("/api/nodes/<node_id>", methods=["GET"])
    def get_node(node_id: str):
        node = registry.get_node(node_id)
        if node is None:
            return _error_response("NODE_NOT_FOUND", f"node {node_id} not found", 404, node_id=node_id)
        return jsonify(node), 200

    @app.route("/api/nodes/<node_id>", methods=["PUT"])
    def update_node(node_id: str):
        payload = request.get_json(silent=True) or {}
        try:
            updated = registry.update_node(node_id, payload)
        except NodeValidationError as exc:
            return _error_response("VALIDATION_ERROR", str(exc), 400, node_id=node_id)
        except KeyError:
            return _error_response("NODE_NOT_FOUND", f"node {node_id} not found", 404, node_id=node_id)
        return jsonify(updated), 200

    @app.route("/api/nodes/<node_id>", methods=["DELETE"])
    def delete_node(node_id: str):
        if not registry.delete_node(node_id):
            return _error_response("NODE_NOT_FOUND", f"node {node_id} not found", 404, node_id=node_id)
        return "", 204

    @app.route("/api/nodes/<node_id>/status", methods=["GET"])
    def node_status(node_id: str):
        node = registry.get_node(node_id)
        if node is None:
            return _error_response("NODE_NOT_FOUND", f"node {node_id} not found", 404, node_id=node_id)

        result, error = _status_for_node(node)
        if error:
            return _error_response(*error)
        return jsonify(result), 200

    @app.route("/api/nodes/<node_id>/actions/<action>", methods=["POST"])
    def node_action(node_id: str, action: str):
        node = registry.get_node(node_id)
        if node is None:
            return _error_response("NODE_NOT_FOUND", f"node {node_id} not found", 404, node_id=node_id)
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
        return jsonify({"node_id": node_id, "action": action, "status_code": status_code, "response": response}), status_code

    @app.route("/api/management/overview", methods=["GET"])
    def management_overview():
        nodes = registry.list_nodes()
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
        summary = {
            "total_nodes": len(nodes),
            "unavailable_nodes": unavailable_nodes,
            "stream_available_nodes": stream_available_count,
        }
        return jsonify({"summary": summary, "nodes": statuses}), 200
