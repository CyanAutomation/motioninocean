"""Management API for Motion In Ocean: webcam registry, discovery, and status aggregation.

Provides REST endpoints for registering remote camera nodes, approving/rejecting
discovered nodes, querying webcam status, and executing actions on remote nodes.
Includes comprehensive SSRF protection, DNS pinning, and secure HTTP request handling.
"""

import http.client
import ipaddress
import json
import logging
import os
import socket
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple, cast
from urllib.parse import urlparse, urlunparse

import sentry_sdk
from flask import Flask, jsonify, request

from .node_registry import FileWebcamRegistry, NodeValidationError, validate_webcam
from .transport_url_validation import parse_docker_url


# SSRF Protection Configuration
# Canonical variable: MIO_ALLOW_PRIVATE_IPS
CANONICAL_ALLOW_PRIVATE_IPS_ENV_VAR = "MIO_ALLOW_PRIVATE_IPS"

logger = logging.getLogger(__name__)


def _parse_env_bool(raw: str) -> bool:
    """Parse a permissive env-var boolean value."""
    return raw.lower() in {"true", "1", "yes"}


def _load_allow_private_ips_flag() -> bool:
    """Load private-IP override flag from canonical environment variable."""
    canonical_raw = os.environ.get(CANONICAL_ALLOW_PRIVATE_IPS_ENV_VAR)
    if canonical_raw is None:
        return False
    return _parse_env_bool(canonical_raw)


ALLOW_PRIVATE_IPS = _load_allow_private_ips_flag()


def is_private_ip_allowed() -> bool:
    """Return whether private IP targets are allowed for SSRF checks.

    Reads the environment at call time so behavior can react to config changes
    deterministically during runtime and tests.

    Returns:
        True when private IP override evaluates to enabled, False otherwise.
    """
    return _load_allow_private_ips_flag()


# Request timeout used for proxied webcam HTTP calls.
REQUEST_TIMEOUT_SECONDS = 5.0


class NodeRequestError(RuntimeError):
    """Raised when a proxied webcam request cannot be completed safely."""


class NodeInvalidResponseError(NodeRequestError):
    """Raised when a proxied webcam responds with malformed JSON payload."""


class NodeConnectivityError(ConnectionError):
    """Raised when a proxied webcam request fails due to network-level connectivity issues."""

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
    """Extract bearer token from Authorization header.

    Returns:
        Bearer token string if present and valid, None otherwise.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.lower().startswith("bearer "):
        return None
    token = auth_header[7:].strip()
    return token or None


def _validate_node_base_url(base_url: str) -> None:
    """Validate webcam base URL for basic format and blocked hosts.

    Args:
        base_url: Node base URL to validate.

    Raises:
        NodeRequestError: If URL is malformed or points to a blocked host.
    """
    parsed = urlparse(base_url)
    hostname = parsed.hostname
    if parsed.scheme not in {"http", "https"} or not hostname:
        message = "webcam target is invalid"
        raise NodeRequestError(message)

    blocked_hosts = {"localhost", "metadata.google.internal", "metadata", "169.254.169.254"}
    if hostname.lower() in blocked_hosts:
        message = "webcam target is not allowed"
        raise NodeRequestError(message)


def _is_blocked_address(raw: Any) -> bool:
    """Check if an IP address is blocked for SSRF protection.

    Blocks: loopback, link-local, multicast, reserved, unspecified.
    Private IPs are blocked unless MIO_ALLOW_PRIVATE_IPS=true.

    Args:
        raw: IP address string or ipaddress object.

    Returns:
        True if address should be blocked, False otherwise.
    """
    ip = ipaddress.ip_address(str(raw))
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
    if is_private_ip_allowed():
        return False

    return ip.is_private


def _vet_resolved_addresses(addresses: Tuple[str, ...]) -> Tuple[str, ...]:
    """Filter resolved IP addresses for SSRF blocks.

    Args:
        addresses: Tuple of resolved IP addresses.

    Returns:
        Tuple of vetted addresses (blocked addresses removed).

    Raises:
        NodeRequestError: If all addresses are blocked.
    """
    vetted: list[str] = []
    for address in addresses:
        if _is_blocked_address(address):
            continue
        if address not in vetted:
            vetted.append(address)

    if not vetted:
        message = "webcam target is not allowed"
        raise NodeRequestError(message)

    return tuple(vetted)  # type: ignore[return-value]


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
                "Set MIO_ALLOW_PRIVATE_IPS=true on the management webcam "
                "to allow LAN/private-IP discovery registrations. Enable only on trusted internal networks."
            ),
            "required_setting": "MIO_ALLOW_PRIVATE_IPS=true",
        },
    )


def _private_announcement_blocked(base_url: str) -> Optional[str]:
    parsed = urlparse(base_url)
    hostname = parsed.hostname
    if not hostname or is_private_ip_allowed():
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
            assert isinstance(resolved_ip, str)  # Assert type for MyPy
            if _is_blocked_address(resolved_ip):
                return resolved_ip
    return None


class _PinnedHTTPConnection(http.client.HTTPConnection):
    """HTTP connection that always connects to a pre-vetted IP address."""

    def __init__(self, host: str, port: Optional[int], connect_host: str, timeout: float):
        super().__init__(host=host, port=port, timeout=timeout)
        self._connect_host = connect_host
        self.port = port or 80

    def connect(self):
        self.sock = socket.create_connection((self._connect_host, self.port), self.timeout)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """HTTPS connection that pins DNS to a vetted IP while preserving SNI hostname."""

    def __init__(
        self,
        host: str,
        port: Optional[int],
        connect_host: str,
        timeout: float,
        context: ssl.SSLContext,
    ):
        super().__init__(host=host, port=port, timeout=timeout, context=context)
        self._connect_host = connect_host
        self.port = port or 443

    def connect(self):
        sock = socket.create_connection((self._connect_host, self.port), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


def _error_response(
    code: str,
    message: str,
    status_code: int,
    webcam_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
):
    """Build standardized error response JSON.

    Args:
        code: Error code (e.g., 'DISCOVERY_PRIVATE_IP_BLOCKED').
        message: Error message.
        status_code: HTTP status code.
        webcam_id: Optional webcam ID for context.
        details: Optional error details dict.

    Returns:
        Tuple of (jsonify response, status_code).
    """
    payload: Dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    }
    if webcam_id:
        payload["error"]["webcam_id"] = webcam_id
    return jsonify(payload), status_code


def _is_registry_corruption_error(exc: NodeValidationError) -> bool:
    return "webcam registry file is corrupted and cannot be parsed" in str(exc)


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
    first_seen = (
        existing_discovery.get("first_seen") or existing.get("last_seen")
        if isinstance(existing, dict)
        else now_iso
    )
    return {
        "source": "manual",
        "first_seen": first_seen or now_iso,
        "last_announce_at": existing_discovery.get("last_announce_at")
        if isinstance(existing_discovery, dict)
        else None,
        "approved": True,
    }


def _discovery_metadata(existing: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    now_iso = _utc_now_iso()
    existing_discovery = existing.get("discovery", {}) if isinstance(existing, dict) else {}
    first_seen = (
        existing_discovery.get("first_seen") or existing.get("last_seen")
        if isinstance(existing, dict)
        else now_iso
    )
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
    """Classify URL/network errors into human-readable categories.

    Args:
        reason: Exception or error reason to classify.

    Returns:
        Tuple of (human_readable_reason, category_code).
    """
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
    if any(
        token in reason_text for token in ("connection refused", "connection reset", "broken pipe")
    ):
        return "connection refused or reset", "connection_refused_or_reset"
    return "connection failed", "network"


def _netloc_has_explicit_port(netloc: str) -> bool:
    """Return True when URL netloc explicitly includes a port segment."""
    host_port = netloc.rsplit("@", 1)[-1]
    if host_port.startswith("["):
        closing_bracket = host_port.find("]")
        if closing_bracket == -1:
            return False
        return host_port[closing_bracket + 1 :].startswith(":")
    return ":" in host_port


def _build_host_header(parsed_url) -> str:
    """Construct RFC-safe Host header without credentials from parsed URL."""
    hostname = parsed_url.hostname
    if not hostname:
        message = "webcam target is invalid"
        raise NodeRequestError(message)

    host = f"[{hostname}]" if ":" in hostname else hostname
    default_port = 443 if parsed_url.scheme == "https" else 80
    explicit_port = _netloc_has_explicit_port(parsed_url.netloc)
    if parsed_url.port is not None and (parsed_url.port != default_port or explicit_port):
        return f"{host}:{parsed_url.port}"
    return host


def _resolve_and_vet_addresses(hostname_str: str, port: Optional[int]) -> Tuple[str, ...]:
    """Resolve hostname and vet resulting IP addresses against SSRF rules.

    Args:
        hostname_str: Hostname to resolve (already validated for blocked addresses).
        port: Optional port number for getaddrinfo.

    Returns:
        Tuple of vetted IP addresses.

    Raises:
        NodeRequestError: If hostname is blocked by SSRF.
        NodeConnectivityError: If DNS resolution fails.
        ConnectionError: If no addresses pass vetting.
    """
    try:
        if _is_blocked_address(hostname_str):
            message = "webcam target is not allowed"
            raise NodeRequestError(message)
        resolved_addresses: Tuple[str, ...] = (hostname_str,)
    except ValueError:
        try:
            records = socket.getaddrinfo(hostname_str, port or None, proto=socket.IPPROTO_TCP)
        except socket.gaierror as exc:
            error_message = "dns resolution failed"
            raise NodeConnectivityError(
                error_message,
                reason="dns resolution failed",
                category="dns",
                raw_error=str(exc),
            ) from exc
        resolved_addresses = tuple(cast("str", record[4][0]) for record in records)

    vetted_addresses: Tuple[str, ...] = _vet_resolved_addresses(tuple(resolved_addresses))
    if not vetted_addresses:
        message = "name resolution returned no addresses"
        raise ConnectionError(message)

    return vetted_addresses


def _attempt_pinned_connection(
    is_https: bool,
    hostname: str,
    port: Optional[int],
    address: str,
    request_target: str,
    headers: Dict[str, str],
    data: Optional[bytes],
    method: str,
    tls_context: Optional[ssl.SSLContext],
) -> Tuple[int, dict]:
    """Attempt single DNS-pinned HTTP(S) connection to address.

    Args:
        is_https: Whether to use HTTPS.
        hostname: Hostname for Host header.
        port: Port number.
        address: IP address to connect to (DNS pinning).
        request_target: HTTP request target path.
        headers: HTTP headers dict.
        data: Request body bytes.
        method: HTTP method.
        tls_context: SSL context (for HTTPS).

    Returns:
        Tuple of (http_status_code, response_json_dict).

    Raises:
        urllib.error.URLError, OSError, ssl.SSLError: Connection errors.
        NodeInvalidResponseError: If response JSON is malformed.
    """
    actual_connection: _PinnedHTTPConnection | _PinnedHTTPSConnection | None = None
    try:
        if is_https:
            actual_connection = _PinnedHTTPSConnection(
                host=hostname,
                port=port,
                connect_host=address,
                timeout=REQUEST_TIMEOUT_SECONDS,
                context=tls_context,
            )
        else:
            actual_connection = _PinnedHTTPConnection(
                host=hostname,
                port=port,
                connect_host=address,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )

        actual_connection.request(method, request_target, body=data, headers=headers)
        response = actual_connection.getresponse()
        body_text = response.read().decode("utf-8")
        if not body_text:
            return response.status, {}
        try:
            body_json = json.loads(body_text)
        except json.JSONDecodeError as exc:
            message = "webcam returned malformed JSON"
            raise NodeInvalidResponseError(message) from exc
        if not isinstance(body_json, dict):
            message = "webcam returned non-object JSON"
            raise NodeInvalidResponseError(message)
        return response.status, body_json
    finally:
        if actual_connection is not None:
            actual_connection.close()


def _request_json(node: Dict[str, Any], method: str, path: str, body: Optional[dict] = None):  # type: ignore
    """Proxy HTTP request to remote webcam with DNS pinning and SSRF protection.

    Performs DNS resolution, validates resolved IPs against SSRF rules, then
    establishes HTTPS/HTTP connection with DNS pinning to prevent response spoofing.

    Args:
        node: Node dict with 'base_url' and optional 'auth' fields.
        method: HTTP method (GET, POST, etc.).
        path: URL path relative to webcam base_url.
        body: Optional request body dict (will be JSON-encoded).

    Returns:
        Tuple of (http_status_code, response_json_dict).

    Raises:
        NodeRequestError: On URL validation or SSRF blocking.
        NodeConnectivityError: On network errors (DNS, connection, TLS).
        NodeInvalidResponseError: If webcam returns invalid JSON.
    """
    base_url = node["base_url"].rstrip("/")
    _validate_node_base_url(base_url)

    # Enrich the current request scope with this webcam's context.
    webcam_id = node.get("id", "unknown")
    current_scope = sentry_sdk.get_current_scope()
    current_scope.set_tag("component", "management")
    current_scope.set_tag("webcam_id", webcam_id)
    current_scope.set_context(
        "node_request",
        {
            "webcam_id": webcam_id,
            "method": method,
            "path": path,
            "base_url": node.get("base_url", "unknown"),
        },
    )

    url = base_url + path
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname
    if not hostname:
        message = "webcam target is invalid"
        raise NodeRequestError(message)

    port = parsed_url.port
    # Explicitly cast hostname to str to help MyPy inference
    hostname_str = str(hostname)

    # Resolve and vet addresses
    vetted_addresses = _resolve_and_vet_addresses(hostname_str, port)

    headers = {"Content-Type": "application/json", **_build_headers(node)}
    headers.setdefault("Host", _build_host_header(parsed_url))
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request_target = (
        urlunparse(("", "", parsed_url.path, parsed_url.params, parsed_url.query, "")) or "/"
    )
    is_https = parsed_url.scheme == "https"
    tls_context = ssl.create_default_context() if is_https else None

    connection_errors = []
    for address in vetted_addresses:
        try:
            return _attempt_pinned_connection(
                is_https=is_https,
                hostname=hostname_str,
                port=port,
                address=address,
                request_target=request_target,
                headers=headers,
                data=data,
                method=method,
                tls_context=tls_context,
            )
        except NodeInvalidResponseError:
            raise
        except (urllib.error.URLError, OSError, ssl.SSLError, ssl.CertificateError) as exc:
            reason_source = exc.reason if isinstance(exc, urllib.error.URLError) else exc
            reason, category = _classify_url_error(reason_source)
            connection_errors.append(
                NodeConnectivityError(
                    reason,
                    reason=reason,
                    category=category,
                    raw_error=str(reason_source),
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

    error_message = "all connection attempts failed"
    raise ConnectionError(error_message)


def _parse_docker_url(base_url: str) -> Tuple[str, int, str]:
    """Backward-compatible wrapper for the shared docker URL parser."""
    return parse_docker_url(base_url)


def _get_docker_container_status(
    proxy_host: str, proxy_port: int, container_id: str, auth_headers: Dict[str, str]
) -> Tuple[int, Dict[str, Any]]:
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
        with urllib.request.urlopen(req, timeout=2.5) as response:  # nosec B310 - URL is pre-validated against SSRF
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
            error_message = "docker proxy connection refused"
            raise NodeConnectivityError(
                error_message,
                reason="connection refused",
                category="connection_refused_or_reset",
                raw_error=reason_msg,
            ) from exc
        if "timed out" in reason_msg.lower():
            error_message = "docker proxy request timed out"
            raise NodeConnectivityError(
                error_message,
                reason="request timed out",
                category="timeout",
                raw_error=reason_msg,
            ) from exc
        error_message = "docker proxy connection failed"
        raise NodeConnectivityError(
            error_message,
            reason="connection failed",
            category="network",
            raw_error=reason_msg,
        ) from exc


def _build_diagnostics_result(webcam_id: str) -> Dict[str, Any]:
    """Create initial diagnostics result structure for a webcam.

    Args:
        webcam_id: Unique identifier for the webcam node.

    Returns:
        Dict with initialized diagnostics structure including registration, URL validation,
        DNS resolution, network connectivity, and API endpoint sections.
    """
    return {
        "webcam_id": webcam_id,
        "diagnostics": {
            "registration": {"valid": False, "status": "fail"},
            "url_validation": {"blocked": False, "status": "pass"},
            "dns_resolution": {"resolves": False, "status": "fail"},
            "network_connectivity": {"reachable": False, "status": "fail"},
            "api_endpoint": {"accessible": False, "status_code": None, "status": "fail"},
        },
        "guidance": [],
        "recommendations": [],
    }


def _check_dns_resolution(hostname: str, port: Optional[int]) -> Tuple[bool, list, Optional[str]]:
    """Resolve hostname to list of IP addresses using DNS.

    Args:
        hostname: DNS hostname to resolve.
        port: Optional port number for socket resolution.

    Returns:
        Tuple of (success: bool, resolved_ips: list, error: Optional[str]).
        On success, resolved_ips contains unique IP addresses; on failure, error_string is set.

    Raises:
        socket.gaierror: Re-raised from socket.getaddrinfo if DNS lookup fails.
    """
    try:
        records = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
        resolved_ips = list({record[4][0] for record in records})
        return True, resolved_ips, None
    except socket.gaierror as exc:
        return False, [], str(exc)


def _check_ssrf_blocking(base_url: str, resolved_ips: list) -> Tuple[bool, str]:
    """Check if URL hostname or resolved IPs are blocked by SSRF protection.

    Args:
        base_url: Full HTTP/HTTPS URL to check.
        resolved_ips: List of IP addresses resolved from hostname.

    Returns:
        Tuple of (is_blocked: bool, reason: str).
    """
    parsed = urlparse(base_url)
    hostname = parsed.hostname

    try:
        if hostname and _is_blocked_address(hostname):
            return True, "private IP or reserved address"
    except ValueError:
        pass  # hostname is not an IP address, which is fine

    for ip in resolved_ips:
        if _is_blocked_address(ip):
            return True, f"resolved to private IP {ip}"

    return False, ""


def _check_api_endpoint(
    node: Dict[str, Any],
) -> Tuple[int, Optional[Dict[str, Any]], Optional[Exception]]:
    """Call the /api/status endpoint on a remote webcam node.

    Args:
        node: Webcam node dict with authentication and config.

    Returns:
        Tuple of (status_code: int, response_payload: Optional[dict], exception: Optional[Exception]).
        On success, response_payload contains the JSON response.
        On exception, exception field contains the error.
    """
    try:
        status_code, payload = _request_json(node, "GET", "/api/status")
        return status_code, payload, None
    except Exception as exc:
        return 0, None, exc


def _diagnose_docker_transport(
    node: Dict[str, Any],
    base_url: str,
    results: Dict[str, Any],
    add_recommendation: Any,
) -> Dict[str, Any]:
    """Diagnose Docker transport connectivity for a webcam node.

    Validates docker URL format, resolves proxy hostname, checks docker socket proxy,
    and tests container status.

    Args:
        node: Webcam node dict with id, base_url, transport, auth token.
        base_url: Docker URL (docker://proxy-host:port/container-id).
        results: Diagnostics results dict to update.
        add_recommendation: Callable to add diagnostic guidance messages.

    Returns:
        Updated results dict with docker-specific diagnostics.
    """
    try:
        proxy_host, proxy_port, container_id = _parse_docker_url(base_url)
        results["diagnostics"]["registration"].update({"valid": True, "status": "pass"})
        results["diagnostics"]["url_validation"].update({"blocked": False, "status": "pass"})
    except ValueError as exc:
        results["diagnostics"]["registration"].update(
            {"valid": False, "status": "fail", "error": str(exc), "code": "INVALID_DOCKER_URL"}
        )
        add_recommendation(
            f"Fix: Invalid docker URL format. Expected: docker://proxy-host:port/container-id. Error: {exc!s}",
            "fail",
            "INVALID_DOCKER_URL",
        )
        return results

    # DNS resolution
    dns_success, resolved_ips, dns_error = _check_dns_resolution(proxy_host, proxy_port)
    if not dns_success:
        results["diagnostics"]["dns_resolution"].update(
            {
                "resolves": False,
                "status": "fail",
                "error": dns_error,
                "code": "DNS_RESOLUTION_FAILED",
            }
        )
        add_recommendation(
            f"Network Issue: DNS failed for docker proxy '{proxy_host}'. Check hostname and network DNS.",
            "fail",
            "DNS_RESOLUTION_FAILED",
        )
        return results

    results["diagnostics"]["dns_resolution"].update(
        {"resolves": True, "status": "pass", "resolved_ips": resolved_ips}
    )

    # Docker container status check
    auth_headers = _build_headers(node)
    try:
        status_code, status_payload = _get_docker_container_status(
            proxy_host, proxy_port, container_id, auth_headers
        )
        results["diagnostics"]["network_connectivity"].update({"reachable": True, "status": "pass"})
        results["diagnostics"]["api_endpoint"].update(
            {
                "accessible": status_code in {200, 404},
                "status_code": status_code,
                "healthy": status_code == 200,
                "status": "pass" if status_code == 200 else "fail",
            }
        )

        if status_code == 200:
            add_recommendation(
                "Docker proxy reachable and container found with status: "
                + status_payload.get("status", "ok"),
                "pass",
            )
        elif status_code == 404:
            results["diagnostics"]["api_endpoint"]["code"] = "DOCKER_CONTAINER_NOT_FOUND"
            add_recommendation(
                f"Container '{container_id}' not found on docker proxy {proxy_host}:{proxy_port}. Check container name.",
                "fail",
                "DOCKER_CONTAINER_NOT_FOUND",
            )
        else:
            results["diagnostics"]["api_endpoint"]["code"] = "UNEXPECTED_STATUS"
            add_recommendation(
                f"Docker proxy returned unexpected status {status_code}.",
                "warn",
                "UNEXPECTED_STATUS",
            )
    except NodeConnectivityError as exc:
        results["diagnostics"]["network_connectivity"].update(
            {
                "reachable": exc.category != "timeout",
                "status": "warn" if exc.category != "timeout" else "fail",
                "error": exc.reason,
                "category": exc.category,
                "code": "NETWORK_CONNECTIVITY_ERROR",
            }
        )
        if exc.raw_error:
            results["diagnostics"]["network_connectivity"]["raw_error"] = _sanitize_error_text(
                exc.raw_error
            )

        guidance_map = {
            "timeout": f"Network Timeout: Docker proxy took longer than {REQUEST_TIMEOUT_SECONDS}s to respond. Check docker proxy service and network latency.",
            "connection_refused_or_reset": "Connection Error: Docker proxy refused connection. Ensure docker-socket-proxy is running on correct port.",
            "network": "Network Error: Unable to reach docker proxy. Check network connectivity and firewall rules.",
        }
        add_recommendation(
            guidance_map.get(exc.category, f"Docker proxy error: {exc.reason}"),
            "fail",
            "NETWORK_CONNECTIVITY_ERROR",
        )

    return results


def _diagnose_http_transport(
    node: Dict[str, Any],
    base_url: str,
    results: Dict[str, Any],
    add_recommendation: Any,
) -> Dict[str, Any]:
    """Diagnose HTTP transport connectivity for a webcam node.

    Validates HTTP URL, checks SSRF blocking, resolves hostname, and tests API endpoint.

    Args:
        node: Webcam node dict with id, base_url, transport, auth token.
        base_url: HTTP or HTTPS URL.
        results: Diagnostics results dict to update.
        add_recommendation: Callable to add diagnostic guidance messages.

    Returns:
        Updated results dict with HTTP-specific diagnostics.
    """
    # Validate URL format
    try:
        _validate_node_base_url(base_url)
        results["diagnostics"]["registration"].update({"valid": True, "status": "pass"})
    except NodeRequestError as exc:
        results["diagnostics"]["registration"].update(
            {"valid": False, "status": "fail", "error": str(exc), "code": "INVALID_BASE_URL"}
        )
        add_recommendation(
            "Fix: Ensure base_url is valid (http:// or https://)", "fail", "INVALID_BASE_URL"
        )
        return results

    # Check SSRF blocking on hostname
    parsed = urlparse(base_url)
    hostname = parsed.hostname
    try:
        if _is_blocked_address(hostname):
            results["diagnostics"]["url_validation"].update(
                {
                    "blocked": True,
                    "status": "fail",
                    "blocked_reason": "private IP or reserved address",
                    "code": "SSRF_BLOCKED",
                }
            )
            if is_private_ip_allowed():
                add_recommendation(
                    "Code detected SSRF block despite ALLOW_PRIVATE_IPS=true. This is unexpected.",
                    "warn",
                    "SSRF_BLOCKED_UNEXPECTED",
                )
            else:
                add_recommendation(
                    "Private IP (192.168.x.x, 10.x.x.x, 172.16.x.x) blocked by SSRF protection. "
                    "Option 1: Use docker network hostname (e.g., 'motion-in-ocean-webcam:8000'). "
                    "Option 2 (internal networks only): Set MIO_ALLOW_PRIVATE_IPS=true in management webcam environment.",
                    "fail",
                    "SSRF_BLOCKED",
                )
            return results
    except ValueError:
        pass

    # DNS resolution
    dns_success, resolved_ips, dns_error = _check_dns_resolution(hostname, parsed.port or None)
    if not dns_success:
        results["diagnostics"]["dns_resolution"].update(
            {
                "resolves": False,
                "status": "fail",
                "error": dns_error,
                "code": "DNS_RESOLUTION_FAILED",
            }
        )
        add_recommendation(
            f"Network Issue: DNS failed for '{hostname}'. Check hostname spelling and network connectivity.",
            "fail",
            "DNS_RESOLUTION_FAILED",
        )
        return results

    results["diagnostics"]["dns_resolution"].update(
        {"resolves": True, "status": "pass", "resolved_ips": resolved_ips}
    )

    # Check SSRF blocking on resolved IPs
    ssrf_blocked, ssrf_reason = _check_ssrf_blocking(base_url, resolved_ips)
    if ssrf_blocked:
        results["diagnostics"]["url_validation"].update(
            {
                "blocked": True,
                "status": "fail",
                "blocked_reason": ssrf_reason,
                "code": "SSRF_BLOCKED",
            }
        )
        if is_private_ip_allowed():
            add_recommendation(
                f"Hostname '{hostname}' resolves to a non-private address type that is blocked ({ssrf_reason}).",
                "warn",
                "SSRF_BLOCKED_UNEXPECTED",
            )
        else:
            add_recommendation(
                f"Hostname '{hostname}' resolves to private IP, blocked by SSRF protection. "
                "Option 1: Use a public IP or docker network hostname. "
                "Option 2 (internal networks only): Set MIO_ALLOW_PRIVATE_IPS=true in management webcam environment.",
                "fail",
                "SSRF_BLOCKED",
            )
        return results

    # Call API endpoint
    status_code, _status_payload, api_exception = _check_api_endpoint(node)

    if api_exception is None:
        # Successful API call
        results["diagnostics"]["network_connectivity"].update({"reachable": True, "status": "pass"})
        results["diagnostics"]["api_endpoint"].update(
            {
                "accessible": status_code in {200, 503},
                "status_code": status_code,
                "healthy": status_code == 200,
                "status": "pass"
                if status_code == 200
                else "warn"
                if status_code == 503
                else "fail",
            }
        )

        if status_code == 200:
            add_recommendation("Node is reachable and responsive. Status check successful.", "pass")
        elif status_code == 503:
            results["diagnostics"]["api_endpoint"]["code"] = "API_STATUS_503"
            add_recommendation(
                "Node is reachable but reported 503 Service Unavailable. Camera may still be initializing.",
                "warn",
                "API_STATUS_503",
            )
        else:
            results["diagnostics"]["api_endpoint"]["code"] = "UNEXPECTED_STATUS"
            add_recommendation(
                f"Node returned unexpected status {status_code}.",
                "warn",
                "UNEXPECTED_STATUS",
            )
        return results

    # Handle exceptions from API call
    if isinstance(api_exception, NodeInvalidResponseError):
        results["diagnostics"]["network_connectivity"].update({"reachable": True, "status": "pass"})
        results["diagnostics"]["api_endpoint"].update(
            {
                "accessible": False,
                "status": "fail",
                "error": "malformed json response",
                "code": "INVALID_JSON_RESPONSE",
            }
        )
        add_recommendation(
            "API Error: Node responded but with invalid JSON. Node may be misconfigured or wrong version.",
            "fail",
            "INVALID_JSON_RESPONSE",
        )
    elif isinstance(api_exception, NodeRequestError):
        results["diagnostics"]["url_validation"].update(
            {
                "blocked": True,
                "status": "fail",
                "blocked_reason": str(api_exception),
                "code": "SSRF_BLOCKED",
            }
        )
        add_recommendation(
            "URL Validation: Node target is blocked by SSRF protection policy.",
            "fail",
            "SSRF_BLOCKED",
        )
    elif isinstance(api_exception, NodeConnectivityError):
        results["diagnostics"]["network_connectivity"].update(
            {
                "reachable": api_exception.category != "timeout",
                "status": "warn" if api_exception.category != "timeout" else "fail",
                "error": api_exception.reason,
                "category": api_exception.category,
                "code": "NETWORK_CONNECTIVITY_ERROR",
            }
        )
        if api_exception.raw_error:
            results["diagnostics"]["network_connectivity"]["raw_error"] = _sanitize_error_text(
                api_exception.raw_error
            )

        guidance_map = {
            "dns": "DNS Resolution: Unable to resolve hostname. Check spelling and network DNS.",
            "timeout": f"Network Timeout: Node took longer than {REQUEST_TIMEOUT_SECONDS}s to respond. Check webcam health, network latency, and camera processing load.",
            "tls": "TLS Error: SSL/TLS handshake failed. Check webcam certificate or use http://.",
            "connection_refused_or_reset": "Connection Error: Node refused connection. Ensure webcam is running on correct port.",
            "network": "Network Error: Unable to reach node. Check network connectivity and firewall rules.",
        }
        add_recommendation(
            guidance_map.get(api_exception.category, f"Network error: {api_exception.reason}"),
            "fail",
            "NETWORK_CONNECTIVITY_ERROR",
        )
    elif isinstance(api_exception, ConnectionError):
        results["diagnostics"]["network_connectivity"].update(
            {
                "reachable": False,
                "status": "fail",
                "error": str(api_exception),
                "code": "NETWORK_CONNECTIVITY_ERROR",
            }
        )
        add_recommendation(
            "Connection: Unable to connect to node. Check webcam is running and network is accessible.",
            "fail",
            "NETWORK_CONNECTIVITY_ERROR",
        )

    return results


def _diagnose_webcam(node: Dict[str, Any]) -> Dict[str, Any]:
    """Perform comprehensive diagnostic checks on a registered webcam.

    Validates webcam registration, URL formatting, DNS resolution, network connectivity,
    and API endpoint accessibility. Returns detailed results and remediation guidance.

    Args:
        node: Webcam dict with id, base_url, transport, etc.

    Returns:
        Dict with diagnostics results, status checks, and troubleshooting guidance.
    """
    webcam_id = node["id"]
    base_url = node.get("base_url", "")
    transport = node.get("transport", "http")

    # Initialize results structure
    results = _build_diagnostics_result(webcam_id)

    # Create closure for adding recommendations
    def _add_recommendation(message: str, status: str, code: Optional[str] = None) -> None:
        results["guidance"].append(message)
        recommendation = {"message": message, "status": status}
        if code:
            recommendation["code"] = code
        results["recommendations"].append(recommendation)

    # Route to appropriate transport handler
    if transport == "docker":
        return _diagnose_docker_transport(node, base_url, results, _add_recommendation)
    return _diagnose_http_transport(node, base_url, results, _add_recommendation)


def _get_docker_status(
    node: Dict[str, Any],
) -> Tuple[Dict[str, Any], Optional[Tuple]]:
    """Fetch status from webcam via Docker API proxy.

    Args:
        node: Webcam dict with docker transport URL and auth.

    Returns:
        Tuple of (status_dict, error_tuple_or_none).
    """
    webcam_id = node["id"]
    base_url = node.get("base_url", "")

    try:
        proxy_host, proxy_port, container_id = _parse_docker_url(base_url)
    except ValueError as exc:
        return {}, (
            "INVALID_DOCKER_URL",
            f"webcam {webcam_id} has an invalid docker URL",
            400,
            webcam_id,
            {
                "reason": str(exc),
                "expected_format": "docker://proxy-hostname:port/container-id",
                "example": "docker://docker-proxy:2375/motion-in-ocean-webcam",
            },
        )

    auth_headers = _build_headers(node)
    try:
        status_code, status_payload = _get_docker_container_status(
            proxy_host, proxy_port, container_id, auth_headers
        )

        if status_code == 200:
            return {
                "webcam_id": webcam_id,
                "status": status_payload.get("status", "ok"),
                "stream_available": bool(status_payload.get("stream_available", False)),
                "status_probe": {"status_code": status_code, "payload": status_payload},
            }, None
        if status_code == 404:
            return {}, (
                "DOCKER_CONTAINER_NOT_FOUND",
                f"container {container_id} not found on docker proxy {proxy_host}:{proxy_port}",
                502,
                webcam_id,
                {"container_id": container_id, "proxy": f"{proxy_host}:{proxy_port}"},
            )
        return {}, (
            "DOCKER_API_ERROR",
            f"docker proxy returned unexpected status {status_code}",
            502,
            webcam_id,
            {"status_code": status_code, "proxy": f"{proxy_host}:{proxy_port}"},
        )
    except NodeConnectivityError as exc:
        return {}, (
            "DOCKER_PROXY_UNREACHABLE",
            f"cannot reach docker proxy at {proxy_host}:{proxy_port}",
            503,
            webcam_id,
            {
                "reason": exc.reason,
                "category": exc.category,
                "raw_error": _sanitize_error_text(exc.raw_error),
                "proxy": f"{proxy_host}:{proxy_port}",
            },
        )


def _get_http_status(
    node: Dict[str, Any],
) -> Tuple[Dict[str, Any], Optional[Tuple]]:
    """Fetch status from webcam via HTTP API.

    Args:
        node: Webcam dict with http transport URL and auth.

    Returns:
        Tuple of (status_dict, error_tuple_or_none).
    """
    webcam_id = node["id"]
    transport = node.get("transport", "http")

    if transport != "http":
        return {}, (
            "TRANSPORT_UNSUPPORTED",
            f"transport '{transport}' is not supported",
            400,
            webcam_id,
            {"transport": transport},
        )

    try:
        status_code, status_payload = _request_json(node, "GET", "/api/status")
    except NodeInvalidResponseError:
        return {}, (
            "WEBCAM_INVALID_RESPONSE",
            f"webcam {webcam_id} returned an invalid response",
            502,
            webcam_id,
            {"reason": "malformed json"},
        )
    except NodeRequestError as exc:
        # Distinguish SSRF blocking from other errors
        error_msg = str(exc).lower()
        if "not allowed" in error_msg or "blocked" in error_msg:
            guidance = (
                "Use docker network hostname (e.g., 'motion-in-ocean-webcam:8000') "
                "or set MIO_ALLOW_PRIVATE_IPS=true in management webcam (internal networks only)"
            )
            return {}, (
                "SSRF_BLOCKED",
                f"webcam {webcam_id} target is blocked by SSRF protection",
                503,
                webcam_id,
                {
                    "reason": "SSRF protection blocks private IPs",
                    "category": "ssrf_blocked",
                    "guidance": guidance,
                },
            )
        return {}, (
            "WEBCAM_UNREACHABLE",
            f"webcam {webcam_id} is unreachable",
            503,
            webcam_id,
            {
                "reason": "target validation failed",
                "category": "invalid_target",
                "raw_error": str(exc),
            },
        )
    except NodeConnectivityError as exc:
        return {}, (
            "NETWORK_UNREACHABLE",
            f"webcam {webcam_id} is unreachable",
            503,
            webcam_id,
            {
                "reason": exc.reason,
                "category": exc.category,
                "raw_error": _sanitize_error_text(exc.raw_error),
            },
        )
    except ConnectionError as exc:
        return {}, (
            "NETWORK_UNREACHABLE",
            f"webcam {webcam_id} is unreachable",
            503,
            webcam_id,
            {
                "reason": "connection failed",
                "category": "network",
                "raw_error": _sanitize_error_text(str(exc)),
            },
        )

    if status_code in {401, 403}:
        return {}, (
            "WEBCAM_UNAUTHORIZED",
            f"webcam {webcam_id} rejected credentials",
            401,
            webcam_id,
            {"status_code": status_code},
        )

    if status_code == 404:
        return {}, (
            "WEBCAM_API_MISMATCH",
            f"webcam {webcam_id} status probe endpoint was not found",
            502,
            webcam_id,
            {
                "expected_endpoint": "/api/status",
                "received_status_code": status_code,
            },
        )

    if status_code == 200:
        return {
            "webcam_id": webcam_id,
            "status": status_payload.get("status", "healthy"),
            "stream_available": bool(status_payload.get("stream_available", False)),
            "status_probe": {"status_code": status_code, "payload": status_payload},
        }, None

    if status_code == 503:
        return {
            "webcam_id": webcam_id,
            "status": status_payload.get("status", "unhealthy"),
            "stream_available": bool(status_payload.get("stream_available", False)),
            "status_probe": {"status_code": status_code, "payload": status_payload},
        }, None

    return {}, (
        "WEBCAM_STATUS_ERROR",
        f"webcam {webcam_id} returned unexpected status response",
        502,
        webcam_id,
        {"status_code": status_code, "path": "/api/status"},
    )


def _status_for_webcam(node: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[Tuple]]:
    """Fetch current status from a remote webcam via HTTP or Docker API.

    Dispatches to transport-specific handlers. Returns webcam status dict or error tuple.

    Args:
        node: Webcam dict with id, base_url, transport, auth, etc.

    Returns:
        Tuple of (status_dict, error_tuple_or_none).
        If successful: (status_dict, None).
        If failed: ({}, (error_code, message, status_code, webcam_id, details)).
    """
    transport = node.get("transport", "http")

    if transport == "docker":
        return _get_docker_status(node)

    return _get_http_status(node)


def register_management_routes(
    app: Flask,
    registry_path: str,
    auth_token: Optional[str] = None,
    node_discovery_shared_secret: Optional[str] = None,
    limiter=None,
) -> None:
    """Register all management API endpoints to Flask app.

    Registers routes for webcam CRUD, discovery announcements, webcam status queries,
    diagnostics, and action proxying. Includes bearer token authentication,
    rate limiting, and SSRF protection.

    Args:
        app: Flask application instance.
        registry_path: Path to persistent webcam registry JSON file.
        auth_token: Optional bearer token for API authentication. If None, auth disabled.
        node_discovery_shared_secret: Optional token for discovery announcements.
        limiter: Optional Flask-Limiter instance for rate limiting.
    """
    registry = FileWebcamRegistry(registry_path)
    discovery_secret = node_discovery_shared_secret
    if discovery_secret is None:
        discovery_secret = os.environ.get("MIO_NODE_DISCOVERY_SHARED_SECRET", "")

    # Helper: Apply rate limit decorator if limiter is available
    def _maybe_limit(limit_str: str):
        def decorator(f):
            if limiter is not None:
                return limiter.limit(limit_str)(f)
            return f

        return decorator

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
            or request.path.startswith("/api/webcams/")
            or request.path == "/api/webcams"
        ):
            return _enforce_management_auth()
        return None

    @app.route("/api/webcams", methods=["GET"])
    @_maybe_limit("1000/minute")
    def list_webcams():
        """List all registered nodes.

        Returns:
            JSON list of all webcam dicts from registry.
        """
        try:
            nodes = registry.list_webcams()
        except NodeValidationError as exc:
            if _is_registry_corruption_error(exc):
                return _registry_corruption_response(exc)
            raise
        return jsonify({"webcams": nodes}), 200

    @app.route("/api/discovery/announce", methods=["POST"])
    @_maybe_limit("10/minute")
    def announce_webcam():
        """Receive webcam self-registration announcement (discovery protocol).

        Creates or updates a webcam registration from a remote node's self-advertisement.
        Validates node, checks SSRF rules, and marks as discovered (not approved by default).

        Returns:
            JSON response with webcam data and approval status.
        """
        unauthorized = _enforce_discovery_auth()
        if unauthorized:
            return unauthorized

        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return _error_response("VALIDATION_ERROR", "webcam payload must be an object", 400)

        candidate = {
            "id": payload.get("webcam_id"),
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
            validated = validate_webcam(candidate)
        except NodeValidationError as exc:
            return _error_response("VALIDATION_ERROR", str(exc), 400)

        blocked_target = _private_announcement_blocked(validated["base_url"])
        if blocked_target:
            return _discovery_private_ip_block_response(validated["base_url"], blocked_target)

        def _build_discovery_upsert_patch(existing: Dict[str, Any]) -> Dict[str, Any]:
            patch = {
                "name": validated["name"],
                "base_url": validated["base_url"],
                "transport": validated["transport"],
                "capabilities": validated["capabilities"],
                "last_seen": validated["last_seen"],
                "labels": validated["labels"],
                "auth": validated["auth"],
            }
            patch["discovery"] = _discovery_metadata(existing)
            return patch

        try:
            upserted = registry.upsert_webcam_from_current(
                validated["id"],
                validated,
                _build_discovery_upsert_patch,
            )
        except NodeValidationError as exc:
            if _is_registry_corruption_error(exc):
                return _registry_corruption_response(exc)
            return _error_response("VALIDATION_ERROR", str(exc), 400, webcam_id=validated["id"])

        status_code = 201 if upserted["upserted"] == "created" else 200
        return jsonify(upserted), status_code

    @app.route("/api/webcams", methods=["POST"])
    @_maybe_limit("100/minute")
    def create_webcam():
        payload = request.get_json(silent=True) or {}
        if "discovery" not in payload:
            payload["discovery"] = _manual_discovery_defaults()
        try:
            created = registry.create_webcam(payload)
        except NodeValidationError as exc:
            if _is_registry_corruption_error(exc):
                return _registry_corruption_response(exc)
            return _error_response("VALIDATION_ERROR", str(exc), 400)
        return jsonify(created), 201

    @app.route("/api/webcams/<webcam_id>", methods=["GET"])
    @_maybe_limit("1000/minute")
    def get_webcam(webcam_id: str):
        try:
            webcam = registry.get_webcam(webcam_id)
        except NodeValidationError as exc:
            if _is_registry_corruption_error(exc):
                return _registry_corruption_response(exc)
            raise
        if webcam is None:
            return _error_response(
                "WEBCAM_NOT_FOUND", f"webcam {webcam_id} not found", 404, webcam_id=webcam_id
            )
        return jsonify(webcam), 200

    @app.route("/api/webcams/<webcam_id>", methods=["PUT"])
    @_maybe_limit("100/minute")
    def update_webcam(webcam_id: str):
        payload = request.get_json(silent=True) or {}

        try:
            existing = registry.get_webcam(webcam_id)
        except NodeValidationError as exc:
            if _is_registry_corruption_error(exc):
                return _registry_corruption_response(exc)
            raise
        if existing and "discovery" not in payload:
            payload["discovery"] = _manual_discovery_defaults(existing)
        try:
            updated = registry.update_webcam(webcam_id, payload)
        except KeyError:
            return _error_response(
                "WEBCAM_NOT_FOUND", f"webcam {webcam_id} not found", 404, webcam_id=webcam_id
            )
        except NodeValidationError as exc:
            if _is_registry_corruption_error(exc):
                return _registry_corruption_response(exc)
            return _error_response("VALIDATION_ERROR", str(exc), 400, webcam_id=webcam_id)
        return jsonify(updated), 200

    @app.route("/api/webcams/<webcam_id>/discovery/<decision>", methods=["POST"])
    @_maybe_limit("100/minute")
    def set_node_discovery_approval(webcam_id: str, decision: str):
        if decision not in {"approve", "reject"}:
            return _error_response(
                "VALIDATION_ERROR", "decision must be approve or reject", 400, webcam_id=webcam_id
            )

        try:
            webcam = registry.get_webcam(webcam_id)
        except NodeValidationError as exc:
            if _is_registry_corruption_error(exc):
                return _registry_corruption_response(exc)
            raise

        if webcam is None:
            return _error_response(
                "WEBCAM_NOT_FOUND", f"webcam {webcam_id} not found", 404, webcam_id=webcam_id
            )

        discovery = webcam.get("discovery", _manual_discovery_defaults(webcam))
        discovery["approved"] = decision == "approve"

        try:
            updated = registry.update_webcam(webcam_id, {"discovery": discovery})
        except NodeValidationError as exc:
            if _is_registry_corruption_error(exc):
                return _registry_corruption_response(exc)
            return _error_response("VALIDATION_ERROR", str(exc), 400, webcam_id=webcam_id)

        return jsonify({"node": updated, "decision": decision}), 200

    @app.route("/api/webcams/<webcam_id>", methods=["DELETE"])
    @_maybe_limit("100/minute")
    def delete_webcam(webcam_id: str):
        try:
            deleted = registry.delete_webcam(webcam_id)
        except NodeValidationError as exc:
            if _is_registry_corruption_error(exc):
                return _registry_corruption_response(exc)
            raise
        if not deleted:
            return _error_response(
                "WEBCAM_NOT_FOUND", f"webcam {webcam_id} not found", 404, webcam_id=webcam_id
            )
        return "", 204

    @app.route("/api/webcams/<webcam_id>/status", methods=["GET"])
    @_maybe_limit("1000/minute")
    def webcam_status(webcam_id: str):
        """Get current status of a registered webcam.

        Queries the webcam for its stream status, camera state, and connectivity.

        Args:
            webcam_id: Unique webcam identifier.

        Returns:
            JSON status dict with stream_available, camera_active, fps, connections, etc.
        """
        try:
            webcam = registry.get_webcam(webcam_id)
        except NodeValidationError as exc:
            if _is_registry_corruption_error(exc):
                return _registry_corruption_response(exc)
            raise
        if webcam is None:
            return _error_response(
                "WEBCAM_NOT_FOUND", f"webcam {webcam_id} not found", 404, webcam_id=webcam_id
            )

        result, error = _status_for_webcam(webcam)
        if error:
            return _error_response(*error)
        return jsonify(result), 200

    @app.route("/api/webcams/<webcam_id>/diagnose", methods=["GET"])
    @_maybe_limit("100/minute")
    def diagnose_webcam(webcam_id: str):
        """
        Perform detailed diagnostics on webcam connectivity and configuration.
        Returns structured diagnostic information and actionable guidance.

        Endpoints:
        - /api/webcams/{webcam_id}/diagnose - comprehensive connectivity diagnostics

        Response:
        - webcam_id: ID of the node
        - diagnostics: nested object with test results
          - registration: URL validation
          - url_validation: SSRF protection screening
          - dns_resolution: hostname resolution
          - network_connectivity: TCP connectivity to node
          - api_endpoint: /api/status endpoint accessibility
        - guidance: list of human-readable recommendations
        """
        try:
            webcam = registry.get_webcam(webcam_id)
        except NodeValidationError as exc:
            if _is_registry_corruption_error(exc):
                return _registry_corruption_response(exc)
            raise
        if webcam is None:
            return _error_response(
                "WEBCAM_NOT_FOUND", f"webcam {webcam_id} not found", 404, webcam_id=webcam_id
            )

        results = _diagnose_webcam(webcam)
        return jsonify(results), 200

    @app.route("/api/webcams/<webcam_id>/actions/<action>", methods=["POST"])
    @_maybe_limit("100/minute")
    def node_action(webcam_id: str, action: str):
        try:
            webcam = registry.get_webcam(webcam_id)
        except NodeValidationError as exc:
            if _is_registry_corruption_error(exc):
                return _registry_corruption_response(exc)
            raise
        if webcam is None:
            return _error_response(
                "WEBCAM_NOT_FOUND", f"webcam {webcam_id} not found", 404, webcam_id=webcam_id
            )
        if webcam.get("transport") != "http":
            return _error_response(
                "TRANSPORT_UNSUPPORTED",
                "actions currently support http transport only",
                400,
                webcam_id=webcam_id,
            )

        payload = request.get_json(silent=True) or {}
        try:
            status_code, response = _request_json(webcam, "POST", f"/api/actions/{action}", payload)
        except NodeInvalidResponseError:
            return _error_response(
                "WEBCAM_INVALID_RESPONSE",
                f"webcam {webcam_id} returned an invalid response",
                502,
                webcam_id=webcam_id,
                details={"reason": "malformed json", "action": action},
            )
        except NodeRequestError:
            return _error_response(
                "WEBCAM_UNREACHABLE",
                f"webcam {webcam_id} is unreachable",
                503,
                webcam_id=webcam_id,
                details={"reason": "target is blocked", "action": action},
            )
        except ConnectionError:
            return _error_response(
                "WEBCAM_UNREACHABLE",
                f"webcam {webcam_id} is unreachable",
                503,
                webcam_id=webcam_id,
                details={"reason": "connection failed", "action": action},
            )

        if status_code in {401, 403}:
            return _error_response(
                "WEBCAM_UNAUTHORIZED",
                f"webcam {webcam_id} rejected credentials",
                401,
                webcam_id=webcam_id,
                details={"action": action, "status_code": status_code},
            )
        return jsonify(
            {
                "webcam_id": webcam_id,
                "action": action,
                "status_code": status_code,
                "response": response,
            }
        ), status_code

    @app.route("/api/management/overview", methods=["GET"])
    @_maybe_limit("100/minute")
    def management_overview():
        try:
            nodes = registry.list_webcams()
        except NodeValidationError as exc:
            if _is_registry_corruption_error(exc):
                return _registry_corruption_response(exc)
            raise
        statuses = []
        unavailable_nodes = 0
        for webcam in nodes:
            result, error = _status_for_webcam(webcam)
            if error:
                unavailable_nodes += 1
                statuses.append(
                    {
                        "webcam_id": webcam["id"],
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
            if "error" not in status
            and str(status.get("status", "")).lower() in {"ok", "healthy", "ready"}
        )
        summary = {
            "total_webcams": len(nodes),
            "unavailable_webcams": unavailable_nodes,
            "healthy_webcams": healthy_nodes,
            "stream_available_webcams": stream_available_count,
        }
        return jsonify({"summary": summary, "webcams": statuses}), 200
