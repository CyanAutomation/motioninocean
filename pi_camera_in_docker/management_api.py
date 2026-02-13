import ipaddress
import json
import os
import ssl
import socket
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse, urlunparse

from flask import Flask, jsonify, request
from node_registry import FileNodeRegistry, NodeValidationError, validate_node


# SSRF Protection Configuration
# Set MOTION_IN_OCEAN_ALLOW_PRIVATE_IPS=true to disable private IP blocking (use only in internal networks)
ALLOW_PRIVATE_IPS = os.environ.get("MOTION_IN_OCEAN_ALLOW_PRIVATE_IPS", "").lower() in {"true", "1", "yes"}

# Request timeout used for proxied node HTTP calls.
REQUEST_TIMEOUT_SECONDS = 5.0


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
    
    # Check always-blocked categories (not configurable)
    always_blocked = (
        ip.is_loopback,
        ip.is_link_local,
        ip.is_multicast,
        ip.is_reserved,
        ip.is_unspecified,
    )
    if any(always_blocked):
        return True
    
    # Private IPs can be allowed if explicitly configured for internal networks
    if ALLOW_PRIVATE_IPS:
        return False
    
    return ip.is_private


def _vet_resolved_addresses(addresses: Tuple[str, ...]) -> Tuple[str, ...]:
    vetted = []
    for address in addresses:
        if _is_blocked_address(address):
            message = "node target is not allowed"
            raise NodeRequestError(message)
        if address not in vetted:
            vetted.append(address)
    return tuple(vetted)


def _discovery_private_ip_block_response(base_url: str, blocked_target: str):
    return _error_response(
        "DISCOVERY_PRIVATE_IP_BLOCKED",
        "discovery announcement blocked: private IP targets are disabled",
        403,
        details={
            "base_url": base_url,
            "blocked_target": blocked_target,
            "reason": "private IP announcements require an explicit opt-in",
            "remediation": (
                "Set MOTION_IN_OCEAN_ALLOW_PRIVATE_IPS=true on the management node "
                "to allow LAN/private-IP discovery registrations. Enable only on trusted internal networks."
            ),
            "required_setting": "MOTION_IN_OCEAN_ALLOW_PRIVATE_IPS=true",
        },
    )


def _private_announcement_blocked(base_url: str) -> Optional[str]:
    parsed = urlparse(base_url)
    hostname = parsed.hostname
    if not hostname or ALLOW_PRIVATE_IPS:
        return None

    try:
        if _is_blocked_address(hostname):
            return hostname
    except ValueError:
        try:
            records = socket.getaddrinfo(hostname, parsed.port or None, proto=socket.IPPROTO_TCP)
        except socket.gaierror:
            # Keep existing registration behavior for unresolved hosts.
            return None
        for record in records:
            resolved_ip = record[4][0]
            if _is_blocked_address(resolved_ip):
                return resolved_ip
    return None


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


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _manual_discovery_defaults(existing: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    now_iso = _utc_now_iso()
    existing_discovery = existing.get("discovery", {}) if isinstance(existing, dict) else {}
    first_seen = existing_discovery.get("first_seen") or existing.get("last_seen") if isinstance(existing, dict) else now_iso
    return {
        "source": "manual",
        "first_seen": first_seen or now_iso,
        "last_announce_at": existing_discovery.get("last_announce_at") if isinstance(existing_discovery, dict) else None,
        "approved": True,
    }


def _discovery_metadata(existing: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    now_iso = _utc_now_iso()
    existing_discovery = existing.get("discovery", {}) if isinstance(existing, dict) else {}
    first_seen = existing_discovery.get("first_seen") or existing.get("last_seen") if isinstance(existing, dict) else now_iso
    approved = existing_discovery.get("approved")
    if not isinstance(approved, bool):
        approved = False
    return {
        "source": "discovered",
        "first_seen": first_seen or now_iso,
        "last_announce_at": now_iso,
        "approved": approved,
    }


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
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as response:
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


def _parse_docker_url(base_url: str) -> Tuple[str, int, str]:
    """
    Parse docker:// URLs to extract proxy host, port, and container ID.
    
    Format: docker://proxy-hostname:port/container-id
    Example: docker://docker-proxy.example.com:2375/motion-in-ocean-webcam
    
    Returns: (hostname, port, container_id)
    Raises: ValueError if URL format is invalid
    """
    parsed = urlparse(base_url)
    if parsed.scheme != "docker":
        raise ValueError(f"Invalid docker URL scheme: {parsed.scheme}. Expected 'docker'.")
    
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("docker URL must include hostname")
    
    port = parsed.port
    if not port:
        raise ValueError("docker URL must include port (e.g., docker://proxy:2375/container-id)")
    
    container_id = parsed.path.lstrip("/")
    if not container_id:
        raise ValueError("docker URL must include container ID (e.g., docker://proxy:2375/container-id)")
    
    return hostname, port, container_id


def _get_docker_container_status(proxy_host: str, proxy_port: int, container_id: str, auth_headers: Dict[str, str]) -> Tuple[int, Dict[str, Any]]:
    """
    Query docker-socket-proxy to get container status.
    
    This connects to a docker-socket-proxy instance and queries the container's state.
    The container must be running to be considered healthy.
    
    Returns: (status_code, status_dict)
    """
    # Use the proxy to get container info
    api_url = f"http://{proxy_host}:{proxy_port}/containers/{container_id}/json"
    
    headers = {"Content-Type": "application/json", **auth_headers}
    
    try:
        req = urllib.request.Request(url=api_url, method="GET", headers=headers)
        with urllib.request.urlopen(req, timeout=2.5) as response:
            payload = response.read().decode("utf-8")
            container_info = json.loads(payload) if payload else {}
            
            # Extract status from container info
            state = container_info.get("State", {})
            running = state.get("Running", False)
            
            # Build status response in motion-in-ocean format
            status_response = {
                "status": "ok" if running else "degraded",
                "app_mode": "webcam",  # Assume webcam for docker containers
                "stream_available": running,
                "camera_active": running,
                "uptime_seconds": 0,  # Not easily available from container info
                "fps": 0,
                "connections": {"current": 0, "max": 0},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "docker_state": state,  # Include raw docker state for debugging
            }
            
            return 200, status_response
            
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8") if exc.fp else ""
        try:
            body_json = json.loads(body_text) if body_text else {}
        except json.JSONDecodeError:
            body_json = {"error": body_text}
        return exc.code, body_json
    except urllib.error.URLError as exc:
        reason_msg = str(exc.reason)
        if "104" in reason_msg or "connection refused" in reason_msg.lower():
            raise NodeConnectivityError(
                "docker proxy connection refused",
                reason="connection refused",
                category="connection_refused_or_reset",
                raw_error=reason_msg,
            )
        if "timed out" in reason_msg.lower():
            raise NodeConnectivityError(
                "docker proxy request timed out",
                reason="request timed out",
                category="timeout",
                raw_error=reason_msg,
            )
        raise NodeConnectivityError(
            "docker proxy connection failed",
            reason="connection failed",
            category="network",
            raw_error=reason_msg,
        )


def _diagnose_node(node: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform detailed diagnostics on a node registration and connectivity.
    Returns detailed information for troubleshooting node connectivity issues.
    """
    node_id = node["id"]
    base_url = node.get("base_url", "")
    transport = node.get("transport", "http")
    results = {
        "node_id": node_id,
        "diagnostics": {
            "registration": {"valid": False},
            "url_validation": {"blocked": False},
            "dns_resolution": {"resolves": False},
            "network_connectivity": {"reachable": False},
            "api_endpoint": {"accessible": False, "status_code": None},
        },
        "guidance": [],
    }

    # Handle docker transport separately
    if transport == "docker":
        try:
            proxy_host, proxy_port, container_id = _parse_docker_url(base_url)
            results["diagnostics"]["registration"]["valid"] = True
            results["diagnostics"]["url_validation"]["blocked"] = False
        except ValueError as exc:
            results["diagnostics"]["registration"]["valid"] = False
            results["diagnostics"]["registration"]["error"] = str(exc)
            results["guidance"].append(f"Fix: Invalid docker URL format. Expected: docker://proxy-host:port/container-id. Error: {str(exc)}")
            return results
        
        # Try DNS resolution of proxy host
        try:
            records = socket.getaddrinfo(proxy_host, proxy_port, proto=socket.IPPROTO_TCP)
            resolved_ips = list(set(record[4][0] for record in records))
            results["diagnostics"]["dns_resolution"]["resolves"] = True
            results["diagnostics"]["dns_resolution"]["resolved_ips"] = resolved_ips
        except socket.gaierror as exc:
            results["diagnostics"]["dns_resolution"]["resolves"] = False
            results["diagnostics"]["dns_resolution"]["error"] = str(exc)
            results["guidance"].append(f"Network Issue: DNS failed for docker proxy '{proxy_host}'. Check hostname and network DNS.")
            return results
        
        # Try to connect to docker proxy
        auth_headers = _build_headers(node)
        try:
            status_code, status_payload = _get_docker_container_status(proxy_host, proxy_port, container_id, auth_headers)
            results["diagnostics"]["network_connectivity"]["reachable"] = True
            results["diagnostics"]["api_endpoint"]["accessible"] = status_code in {200, 404}
            results["diagnostics"]["api_endpoint"]["status_code"] = status_code
            results["diagnostics"]["api_endpoint"]["healthy"] = status_code == 200
            
            if status_code == 200:
                results["guidance"].append("✓ Docker proxy reachable and container found with status: " + status_payload.get("status", "ok"))
            elif status_code == 404:
                results["guidance"].append(f"Container '{container_id}' not found on docker proxy {proxy_host}:{proxy_port}. Check container name.")
            else:
                results["guidance"].append(f"Docker proxy returned unexpected status {status_code}.")
        except NodeConnectivityError as exc:
            results["diagnostics"]["network_connectivity"]["reachable"] = exc.category != "timeout"
            results["diagnostics"]["network_connectivity"]["error"] = exc.reason
            results["diagnostics"]["network_connectivity"]["category"] = exc.category
            if exc.raw_error:
                results["diagnostics"]["network_connectivity"]["raw_error"] = _sanitize_error_text(exc.raw_error)
            
            guidance_map = {
                "timeout": f"Network Timeout: Docker proxy took longer than {REQUEST_TIMEOUT_SECONDS}s to respond. Check docker proxy service and network latency.",
                "connection_refused_or_reset": "Connection Error: Docker proxy refused connection. Ensure docker-socket-proxy is running on correct port.",
                "network": "Network Error: Unable to reach docker proxy. Check network connectivity and firewall rules.",
            }
            results["guidance"].append(guidance_map.get(exc.category, f"Docker proxy error: {exc.reason}"))
        
        return results
    
    # Handle HTTP transport (original logic)
    # Check registration validity
    try:
        _validate_node_base_url(base_url)
        results["diagnostics"]["registration"]["valid"] = True
    except NodeRequestError as exc:
        results["diagnostics"]["registration"]["valid"] = False
        results["diagnostics"]["registration"]["error"] = str(exc)
        results["guidance"].append("Fix: Ensure base_url is valid (http:// or https://)")
        return results

    # Check URL vetting (SSRF protection)
    parsed = urlparse(base_url)
    hostname = parsed.hostname
    try:
        if _is_blocked_address(hostname):
            results["diagnostics"]["url_validation"]["blocked"] = True
            results["diagnostics"]["url_validation"]["blocked_reason"] = "private IP or reserved address"
            if ALLOW_PRIVATE_IPS:
                results["guidance"].append(
                    "WARNING: Code detected SSRF block despite ALLOW_PRIVATE_IPS=true. This is unexpected."
                )
            else:
                results["guidance"].append(
                    "WARNING: Private IP (192.168.x.x, 10.x.x.x, 172.16.x.x) blocked by SSRF protection. "
                    "Option 1: Use docker network hostname (e.g., 'motion-in-ocean-webcam:8000'). "
                    "Option 2 (internal networks only): Set MOTION_IN_OCEAN_ALLOW_PRIVATE_IPS=true in management node environment."
                )
            return results
    except ValueError:
        pass

    # Try DNS resolution
    try:
        records = socket.getaddrinfo(hostname, parsed.port or None, proto=socket.IPPROTO_TCP)
        resolved_ips = list(set(record[4][0] for record in records))
        results["diagnostics"]["dns_resolution"]["resolves"] = True
        results["diagnostics"]["dns_resolution"]["resolved_ips"] = resolved_ips
        
        # Check if resolved IPs are blocked
        for ip in resolved_ips:
            if _is_blocked_address(ip):
                results["diagnostics"]["url_validation"]["blocked"] = True
                results["diagnostics"]["url_validation"]["blocked_reason"] = f"resolved to private IP {ip}"
                if ALLOW_PRIVATE_IPS:
                    results["guidance"].append(
                        f"WARNING: Hostname '{hostname}' resolves to a non-private address type that is blocked ({ip})."
                    )
                else:
                    results["guidance"].append(
                        f"WARNING: Hostname '{hostname}' resolves to private IP {ip}, blocked by SSRF protection. "
                        "Option 1: Use a public IP or docker network hostname. "
                        "Option 2 (internal networks only): Set MOTION_IN_OCEAN_ALLOW_PRIVATE_IPS=true in management node environment."
                    )
                return results
    except socket.gaierror as exc:
        results["diagnostics"]["dns_resolution"]["resolves"] = False
        results["diagnostics"]["dns_resolution"]["error"] = str(exc)
        results["guidance"].append(f"Network Issue: DNS failed for '{hostname}'. Check hostname spelling and network connectivity.")
        return results

    # Try actual connectivity
    try:
        status_code, status_payload = _request_json(node, "GET", "/api/status")
        results["diagnostics"]["network_connectivity"]["reachable"] = True
        results["diagnostics"]["api_endpoint"]["accessible"] = status_code in {200, 503}
        results["diagnostics"]["api_endpoint"]["status_code"] = status_code
        results["diagnostics"]["api_endpoint"]["healthy"] = status_code == 200
        
        if status_code == 200:
            results["guidance"].append("✓ Node is reachable and responsive. Status check successful.")
        elif status_code == 503:
            results["guidance"].append("Node is reachable but reported 503 Service Unavailable. Camera may still be initializing.")
        else:
            results["guidance"].append(f"Node returned unexpected status {status_code}.")
    except NodeInvalidResponseError:
        results["diagnostics"]["network_connectivity"]["reachable"] = True
        results["diagnostics"]["api_endpoint"]["accessible"] = False
        results["diagnostics"]["api_endpoint"]["error"] = "malformed json response"
        results["guidance"].append("API Error: Node responded but with invalid JSON. Node may be misconfigured or wrong version.")
    except NodeRequestError as exc:
        results["diagnostics"]["url_validation"]["blocked"] = True
        results["diagnostics"]["url_validation"]["blocked_reason"] = str(exc)
        results["guidance"].append("URL Validation: Node target is blocked by SSRF protection policy.")
    except NodeConnectivityError as exc:
        results["diagnostics"]["network_connectivity"]["reachable"] = exc.category != "timeout"
        results["diagnostics"]["network_connectivity"]["error"] = exc.reason
        results["diagnostics"]["network_connectivity"]["category"] = exc.category
        if exc.raw_error:
            results["diagnostics"]["network_connectivity"]["raw_error"] = _sanitize_error_text(exc.raw_error)
        
        guidance_map = {
            "dns": "DNS Resolution: Unable to resolve hostname. Check spelling and network DNS.",
            "timeout": f"Network Timeout: Node took longer than {REQUEST_TIMEOUT_SECONDS}s to respond. Check node health, network latency, and camera processing load.",
            "tls": "TLS Error: SSL/TLS handshake failed. Check node certificate or use http://.",
            "connection_refused_or_reset": "Connection Error: Node refused connection. Ensure node is running on correct port.",
            "network": "Network Error: Unable to reach node. Check network connectivity and firewall rules.",
        }
        results["guidance"].append(guidance_map.get(exc.category, f"Network error: {exc.reason}"))
    except ConnectionError as exc:
        results["diagnostics"]["network_connectivity"]["reachable"] = False
        results["diagnostics"]["network_connectivity"]["error"] = str(exc)
        results["guidance"].append("Connection: Unable to connect to node. Check node is running and network is accessible.")

    return results


def _status_for_node(node: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[Tuple]]:
    node_id = node["id"]
    transport = node.get("transport", "http")
    base_url = node.get("base_url", "")
    
    # Handle docker transport
    if transport == "docker":
        try:
            proxy_host, proxy_port, container_id = _parse_docker_url(base_url)
        except ValueError as exc:
            return {}, (
                "INVALID_DOCKER_URL",
                f"node {node_id} has an invalid docker URL",
                400,
                node_id,
                {
                    "reason": str(exc),
                    "expected_format": "docker://proxy-hostname:port/container-id",
                    "example": "docker://docker-proxy:2375/motion-in-ocean-webcam",
                },
            )
        
        auth_headers = _build_headers(node)
        try:
            status_code, status_payload = _get_docker_container_status(proxy_host, proxy_port, container_id, auth_headers)
            
            if status_code == 200:
                return {
                    "node_id": node_id,
                    "status": status_payload.get("status", "ok"),
                    "stream_available": bool(status_payload.get("stream_available", False)),
                    "status_probe": {"status_code": status_code, "payload": status_payload},
                }, None
            elif status_code == 404:
                return {}, (
                    "DOCKER_CONTAINER_NOT_FOUND",
                    f"container {container_id} not found on docker proxy {proxy_host}:{proxy_port}",
                    502,
                    node_id,
                    {"container_id": container_id, "proxy": f"{proxy_host}:{proxy_port}"},
                )
            else:
                return {}, (
                    "DOCKER_API_ERROR",
                    f"docker proxy returned unexpected status {status_code}",
                    502,
                    node_id,
                    {"status_code": status_code, "proxy": f"{proxy_host}:{proxy_port}"},
                )
        except NodeConnectivityError as exc:
            return {}, (
                "DOCKER_PROXY_UNREACHABLE",
                f"cannot reach docker proxy at {proxy_host}:{proxy_port}",
                503,
                node_id,
                {
                    "reason": exc.reason,
                    "category": exc.category,
                    "raw_error": _sanitize_error_text(exc.raw_error),
                    "proxy": f"{proxy_host}:{proxy_port}",
                },
            )
    
    # Handle HTTP transport (original logic)
    if transport != "http":
        return {
            "node_id": node_id,
            "transport": transport,
            "status": "unknown",
            "stream_available": False,
            "error": {
                "code": "TRANSPORT_UNSUPPORTED",
                "message": f"transport '{transport}' is not supported",
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
    except NodeRequestError as exc:
        # Distinguish SSRF blocking from other errors
        error_msg = str(exc).lower()
        if "not allowed" in error_msg or "blocked" in error_msg:
            guidance = (
                "Use docker network hostname (e.g., 'motion-in-ocean-webcam:8000') "
                "or set MOTION_IN_OCEAN_ALLOW_PRIVATE_IPS=true in management node (internal networks only)"
            )
            return {}, (
                "SSRF_BLOCKED",
                f"node {node_id} target is blocked by SSRF protection",
                503,
                node_id,
                {
                    "reason": "SSRF protection blocks private IPs",
                    "category": "ssrf_blocked",
                    "guidance": guidance,
                },
            )
        return {}, (
            "NODE_UNREACHABLE",
            f"node {node_id} is unreachable",
            503,
            node_id,
            {
                "reason": "target validation failed",
                "category": "invalid_target",
                "raw_error": str(exc),
            },
        )
    except NodeConnectivityError as exc:
        return {}, (
            "NETWORK_UNREACHABLE",
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
            "NETWORK_UNREACHABLE",
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
    app: Flask,
    registry_path: str,
    auth_token: str = "",
    node_discovery_shared_secret: Optional[str] = None,
) -> None:
    registry = FileNodeRegistry(registry_path)
    discovery_secret = node_discovery_shared_secret
    if discovery_secret is None:
        discovery_secret = os.environ.get("NODE_DISCOVERY_SHARED_SECRET", "")

    def _enforce_management_auth() -> Optional[Tuple[Any, int]]:
        # Auth is required if and only if token is non-empty
        if not auth_token:
            return None
        token = _extract_bearer_token()
        if token is None or token != auth_token:
            return _error_response("UNAUTHORIZED", "authentication required", 401)
        return None

    def _enforce_discovery_auth() -> Optional[Tuple[Any, int]]:
        token = _extract_bearer_token()
        if token is None or not discovery_secret or token != discovery_secret:
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

    @app.route("/api/discovery/announce", methods=["POST"])
    def announce_node():
        unauthorized = _enforce_discovery_auth()
        if unauthorized:
            return unauthorized

        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return _error_response("VALIDATION_ERROR", "node payload must be an object", 400)

        candidate = {
            "id": payload.get("node_id"),
            "name": payload.get("name"),
            "base_url": payload.get("base_url"),
            "transport": payload.get("transport"),
            "capabilities": payload.get("capabilities"),
            "last_seen": _utc_now_iso(),
            "labels": payload.get("labels", {}),
            "auth": payload.get("auth", {"type": "none"}),
            "discovery": _discovery_metadata(),
        }
        try:
            validated = validate_node(candidate)
        except NodeValidationError as exc:
            return _error_response("VALIDATION_ERROR", str(exc), 400)

        blocked_target = _private_announcement_blocked(validated["base_url"])
        if blocked_target:
            return _discovery_private_ip_block_response(validated["base_url"], blocked_target)

        patch = {
            "name": validated["name"],
            "base_url": validated["base_url"],
            "transport": validated["transport"],
            "capabilities": validated["capabilities"],
            "last_seen": validated["last_seen"],
            "labels": validated["labels"],
            "auth": validated["auth"],
            "discovery": {
                "source": "discovered",
                "last_announce_at": _utc_now_iso(),
            },
        }
        try:
            upserted = registry.upsert_node(validated["id"], validated, patch)
        except NodeValidationError as exc:
            if _is_registry_corruption_error(exc):
                return _registry_corruption_response(exc)
            return _error_response("VALIDATION_ERROR", str(exc), 400, node_id=validated["id"])

        status_code = 201 if upserted["upserted"] == "created" else 200
        return jsonify(upserted), status_code

    @app.route("/api/nodes", methods=["POST"])
    def create_node():
        payload = request.get_json(silent=True) or {}
        if "discovery" not in payload:
            payload["discovery"] = _manual_discovery_defaults()
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
        if existing and "discovery" not in payload:
            payload["discovery"] = _manual_discovery_defaults(existing)
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

    @app.route("/api/nodes/<node_id>/discovery/<decision>", methods=["POST"])
    def set_node_discovery_approval(node_id: str, decision: str):
        if decision not in {"approve", "reject"}:
            return _error_response("VALIDATION_ERROR", "decision must be approve or reject", 400, node_id=node_id)

        try:
            node = registry.get_node(node_id)
        except NodeValidationError as exc:
            if _is_registry_corruption_error(exc):
                return _registry_corruption_response(exc)
            raise

        if node is None:
            return _error_response("NODE_NOT_FOUND", f"node {node_id} not found", 404, node_id=node_id)

        discovery = node.get("discovery", _manual_discovery_defaults(node))
        discovery["approved"] = decision == "approve"

        try:
            updated = registry.update_node(node_id, {"discovery": discovery})
        except NodeValidationError as exc:
            if _is_registry_corruption_error(exc):
                return _registry_corruption_response(exc)
            return _error_response("VALIDATION_ERROR", str(exc), 400, node_id=node_id)

        return jsonify({"node": updated, "decision": decision}), 200

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

    @app.route("/api/nodes/<node_id>/diagnose", methods=["GET"])
    def diagnose_node(node_id: str):
        """
        Perform detailed diagnostics on node connectivity and configuration.
        Returns structured diagnostic information and actionable guidance.
        
        Endpoints:
        - /api/nodes/{node_id}/diagnose - comprehensive connectivity diagnostics
        
        Response:
        - node_id: ID of the node
        - diagnostics: nested object with test results
          - registration: URL validation
          - url_validation: SSRF protection screening
          - dns_resolution: hostname resolution
          - network_connectivity: TCP connectivity to node
          - api_endpoint: /api/status endpoint accessibility
        - guidance: list of human-readable recommendations
        """
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

        results = _diagnose_node(node)
        return jsonify(results), 200

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
