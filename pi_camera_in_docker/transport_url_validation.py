import re
from ipaddress import ip_address
from typing import Tuple
from urllib.parse import ParseResult, urlparse


_DOCKER_CONTAINER_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_HOSTNAME_LABEL_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,63}$")


def _is_valid_http_hostname(hostname: str) -> bool:
    """Return True when hostname is a valid DNS label sequence, localhost, or IP literal."""
    try:
        ip_address(hostname)
    except ValueError:
        lowered = hostname.lower()
    else:
        return True
    if lowered == "localhost":
        return True

    if lowered.endswith("."):
        lowered = lowered[:-1]

    if not lowered:
        return False

    labels = lowered.split(".")
    if any(not label for label in labels):
        return False

    for label in labels:
        if not _HOSTNAME_LABEL_PATTERN.fullmatch(label):
            return False
        if label.startswith("-") or label.endswith("-"):
            return False

    return True


def validate_http_url_shape(url: str, *, field_name: str = "URL") -> ParseResult:
    """Validate the network shape shared by outbound HTTP URLs.

    This validation deliberately does not reject localhost or private addresses. Callers
    that cross an SSRF trust boundary must apply their separate address-policy checks.

    Args:
        url: HTTP or HTTPS URL to validate.
        field_name: Name used in validation error messages.

    Returns:
        Parsed URL after its scheme, hostname, credentials, and port are validated.

    Raises:
        ValueError: If the URL is malformed or is not a credential-free HTTP(S) URL.
    """
    try:
        parsed = urlparse(url)
        port = parsed.port
    except ValueError as exc:
        error_message = f"{field_name} contains an invalid port or malformed host"
        raise ValueError(error_message) from exc

    if parsed.scheme not in {"http", "https"}:
        error_message = f"{field_name} scheme must be http or https"
        raise ValueError(error_message)
    if not parsed.hostname:
        error_message = f"{field_name} must include a valid hostname"
        raise ValueError(error_message)
    if not _is_valid_http_hostname(parsed.hostname):
        error_message = f"{field_name} hostname is invalid"
        raise ValueError(error_message)
    if parsed.username is not None or parsed.password is not None:
        error_message = f"{field_name} must not include embedded credentials"
        raise ValueError(error_message)
    if port is not None and not 1 <= port <= 65535:
        error_message = f"{field_name} port must be between 1 and 65535"
        raise ValueError(error_message)

    return parsed


def parse_docker_url(base_url: str) -> Tuple[str, int, str]:
    """Parse docker:// URLs into proxy host, port, and container ID."""
    parsed = urlparse(base_url)
    if parsed.scheme != "docker":
        error_message = f"Invalid docker URL scheme: {parsed.scheme}. Expected 'docker'."
        raise ValueError(error_message)

    hostname = parsed.hostname
    error_message = "docker URL must include hostname"
    if not hostname:
        raise ValueError(error_message)

    port = parsed.port
    error_message = "docker URL must include port (e.g., docker://proxy:2375/container-id)"
    if not port:
        raise ValueError(error_message)

    if parsed.query or parsed.fragment:
        error_message = "docker URL must not include query or fragment"
        raise ValueError(error_message)

    if not parsed.path or parsed.path == "/":
        error_message = (
            "docker URL must include container ID (e.g., docker://proxy:2375/container-id)"
        )
        raise ValueError(error_message)

    path_segments = [segment for segment in parsed.path.split("/") if segment]

    # Check for forbidden traversal tokens in the raw path before checking segment count,
    # so paths like ../../images/json are caught with a clear "forbidden characters" message.
    lowered_path = parsed.path.lower()
    disallowed_tokens = ("..", "\\", "%2f", "%2e", "?", "#")
    if any(token in lowered_path for token in disallowed_tokens):
        error_message = "docker URL container ID contains forbidden characters"
        raise ValueError(error_message)

    if len(path_segments) != 1 or parsed.path != f"/{path_segments[0]}":
        error_message = "docker URL container ID contains forbidden characters"
        raise ValueError(error_message)

    container_id = path_segments[0]
    lowered_container_id = container_id.lower()
    if any(token in lowered_container_id for token in disallowed_tokens):
        error_message = "docker URL container ID contains forbidden characters"
        raise ValueError(error_message)

    if not _DOCKER_CONTAINER_ID_PATTERN.fullmatch(container_id):
        error_message = "docker URL container ID must match [A-Za-z0-9][A-Za-z0-9._-]*"
        raise ValueError(error_message)

    return hostname, port, container_id


def validate_base_url_for_transport(base_url: str, transport: str) -> None:
    """Validate base URL format matches transport protocol.

    Ensures URL scheme is compatible with the transport type:
    - HTTP transport requires http:// or https:// scheme.
    - Docker transport requires docker:// scheme with valid docker URL structure
      (hostname, port, container ID per docker://host:port/container-id format).

    Args:
        base_url: Full URL string to validate.
        transport: Transport type ('http' or 'docker').

    Raises:
        ValueError: If transport is unsupported, URL scheme doesn't match transport type,
            or docker:// URL is malformed.
    """
    if transport == "http":
        parsed = validate_http_url_shape(base_url, field_name="base_url")

        if parsed.query or parsed.fragment:
            error_message = "base_url must not include query or fragment"
            raise ValueError(error_message)

        if parsed.path and not parsed.path.startswith("/"):
            error_message = "base_url path must start with '/'"
            raise ValueError(error_message)

        if "/../" in parsed.path or parsed.path.startswith("../") or parsed.path.endswith("/.."):
            error_message = "base_url path must not include parent-directory traversal"
            raise ValueError(error_message)

        return

    if transport == "docker":
        error_message = "base_url must start with docker://"
        if not base_url.startswith("docker://"):
            raise ValueError(error_message)
        parse_docker_url(base_url)
        return

    error_message = f"Unsupported transport '{transport}'. Expected one of: http, docker"
    raise ValueError(error_message)
