import json

import pytest

from pi_camera_in_docker import management_api, node_registry
from pi_camera_in_docker.node_registry import NodeValidationError, validate_webcam
from pi_camera_in_docker.transport_url_validation import (
    parse_docker_url,
    validate_base_url_for_transport,
)


@pytest.mark.parametrize(
    "docker_url",
    [
        "docker://proxy:2375/../../images/json",
        "docker://proxy:2375/%2e%2e%2fimages%2fjson",
        "docker://proxy:2375/container/extra",
    ],
)
def test_parse_docker_url_rejects_malicious_container_paths(docker_url):
    with pytest.raises(ValueError, match="docker URL container ID contains forbidden characters"):
        parse_docker_url(docker_url)


def test_get_docker_container_status_url_encodes_container_id(monkeypatch):
    captured = {}

    class DummyResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps({"State": {"Running": True}}).encode("utf-8")

    def fake_request(url, method, headers):
        captured["url"] = url

        class RequestObj:
            full_url = url

        return RequestObj()

    def fake_urlopen(req, timeout):
        return DummyResponse()

    monkeypatch.setattr(management_api.urllib.request, "Request", fake_request)
    monkeypatch.setattr(management_api.urllib.request, "urlopen", fake_urlopen)

    status_code, payload = management_api._get_docker_container_status(
        "proxy",
        2375,
        "container id",
        {},
    )

    assert status_code == 200
    assert payload["status"] == "ok"
    assert captured["url"] == "http://proxy:2375/containers/container%20id/json"


@pytest.mark.parametrize("transport", ["ssh", "https", "", "HTTP"])
def test_validate_base_url_for_transport_rejects_unknown_transport(transport):
    with pytest.raises(ValueError, match=rf"Unsupported transport '{transport}'"):
        validate_base_url_for_transport("http://example.com", transport)


def test_validate_webcam_propagates_unknown_transport_base_url_validation_failure(monkeypatch):
    monkeypatch.setattr(node_registry, "ALLOWED_TRANSPORTS", {"http", "docker", "ssh"})

    with pytest.raises(NodeValidationError, match="Unsupported transport 'ssh'"):
        validate_webcam(
            {
                "id": "node-unknown-transport",
                "name": "Unknown Transport Node",
                "base_url": "http://example.com",
                "auth": {"type": "none"},
                "labels": {},
                "last_seen": "2024-01-01T00:00:00+00:00",
                "capabilities": ["stream"],
                "transport": "ssh",
            }
        )
