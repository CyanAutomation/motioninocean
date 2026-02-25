import re
from typing import Tuple
from urllib.parse import urlparse


_DOCKER_CONTAINER_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


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
        error_message = "base_url must start with http:// or https://"
        if not base_url.startswith(("http://", "https://")):
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
