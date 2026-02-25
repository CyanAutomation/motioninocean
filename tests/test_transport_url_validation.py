import json

import pytest

from pi_camera_in_docker import management_api
from pi_camera_in_docker.transport_url_validation import parse_docker_url


@pytest.mark.parametrize(
    "docker_url",
    [
        "docker://proxy:2375/../../images/json",
        "docker://proxy:2375/%2e%2e%2fimages%2fjson",
        "docker://proxy:2375/container/extra",
    ],
)
def test_parse_docker_url_rejects_malicious_container_paths(docker_url):
    with pytest.raises(ValueError):
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
