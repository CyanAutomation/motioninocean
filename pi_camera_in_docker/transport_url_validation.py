from typing import Tuple
from urllib.parse import urlparse


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

    container_id = parsed.path.lstrip("/")
        error_message = "docker URL must include container ID (e.g., docker://proxy:2375/container-id)"
        if not container_id:
            raise ValueError(error_message)

    return hostname, port, container_id


def validate_base_url_for_transport(base_url: str, transport: str) -> None:
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
