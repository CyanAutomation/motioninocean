from typing import Tuple
from urllib.parse import urlparse


def parse_docker_url(base_url: str) -> Tuple[str, int, str]:
    """Parse docker:// URLs into proxy host, port, and container ID."""
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


def validate_base_url_for_transport(base_url: str, transport: str) -> None:
    if transport == "http":
        if not base_url.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")
        return

    if transport == "docker":
        if not base_url.startswith("docker://"):
            raise ValueError("base_url must start with docker://")
        parse_docker_url(base_url)

