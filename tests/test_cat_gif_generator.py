"""Unit tests for cat GIF retrieval safety."""

from unittest.mock import MagicMock

import pytest

from pi_camera_in_docker import cat_gif_generator


@pytest.mark.parametrize(
    "api_url",
    [
        "http://cats.example/cat.gif",
        "https://cats.example/cat.gif",
    ],
)
def test_fetch_cat_gif_opens_http_urls(monkeypatch, api_url):
    """HTTP and HTTPS URLs should reach the opener after validation."""
    response = MagicMock()
    response.__enter__.return_value.read.return_value = b"gif data"
    opener = MagicMock(return_value=response)
    monkeypatch.setattr(cat_gif_generator.urllib.request, "urlopen", opener)

    assert cat_gif_generator.fetch_cat_gif(api_url, timeout=2.0) == b"gif data"
    opener.assert_called_once_with(api_url, timeout=2.0)


@pytest.mark.parametrize(
    "api_url",
    [
        "file:///etc/passwd",
        "gopher://cats.example/cat.gif",
        "https:///cat.gif",
        "https://user@cats.example/cat.gif",
        "https://user:secret@cats.example/cat.gif",
    ],
)
def test_fetch_cat_gif_rejects_unsafe_urls_without_opening(monkeypatch, api_url):
    """Unsafe URLs should gracefully fail before invoking the opener."""
    opener = MagicMock()
    monkeypatch.setattr(cat_gif_generator.urllib.request, "urlopen", opener)

    assert cat_gif_generator.fetch_cat_gif(api_url) is None
    opener.assert_not_called()
