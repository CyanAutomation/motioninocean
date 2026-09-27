"""Integration tests for frontend asset URL versioning and caching."""

import re

from pi_camera_in_docker.asset_versioning import (
    IMMUTABLE_CACHE_CONTROL,
    REVALIDATE_CACHE_CONTROL,
)
from pi_camera_in_docker.main import _create_base_app, create_webcam_app


def test_rendered_templates_use_current_asset_version(full_config):
    """Webcam, management, and API docs pages version every static reference."""
    app = create_webcam_app(full_config)
    version = app.config["ASSET_VERSION"]

    with app.test_client() as client:
        pages = [
            client.get("/").get_data(as_text=True),
            client.get("/api/docs").get_data(as_text=True),
        ]

    full_config["app_mode"] = "management"
    management_app, _, _ = _create_base_app(full_config)
    with management_app.test_client() as client:
        pages.append(client.get("/").get_data(as_text=True))

    for page in pages:
        static_urls = re.findall(r'["\'](/static/[^"\']+)["\']', page)
        assert static_urls
        assert all(url.endswith(f"?v={version}") for url in static_urls)


def test_versioned_static_response_is_immutable(full_config):
    """A static URL carrying the current version has a one-year immutable policy."""
    app, _, _ = _create_base_app(full_config)
    version = app.config["ASSET_VERSION"]

    response = app.test_client().get(f"/static/css/base.css?v={version}")

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == IMMUTABLE_CACHE_CONTROL


def test_unversioned_or_stale_static_response_revalidates(full_config):
    """Static URLs without the current version cannot be served stale."""
    app, _, _ = _create_base_app(full_config)
    client = app.test_client()

    assert client.get("/static/css/base.css").headers["Cache-Control"] == REVALIDATE_CACHE_CONTROL
    assert (
        client.get("/static/css/base.css?v=previous").headers["Cache-Control"]
        == REVALIDATE_CACHE_CONTROL
    )
