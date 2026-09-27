"""Unit tests for cat GIF retrieval and resource safety."""

import io
from unittest.mock import MagicMock

import pytest
from PIL import Image

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
    entered_response = response.__enter__.return_value
    entered_response.headers = {}
    entered_response.read.side_effect = [b"gif ", b"data", b""]
    opener = MagicMock(return_value=response)
    monkeypatch.setattr(cat_gif_generator.urllib.request, "urlopen", opener)

    assert cat_gif_generator.fetch_cat_gif(api_url, timeout=2.0) == b"gif data"
    opener.assert_called_once_with(api_url, timeout=2.0)


def _gif_bytes(frame_count=1, size=(2, 2)):
    """Build a small animated GIF for resource-limit tests."""
    frames = [Image.new("RGB", size, (index, 0, 0)) for index in range(frame_count)]
    output = io.BytesIO()
    frames[0].save(output, format="GIF", save_all=True, append_images=frames[1:], duration=10)
    return output.getvalue()


def test_fetch_cat_gif_aborts_oversized_download(monkeypatch):
    """Streaming download stops as soon as its byte budget is exceeded."""
    response = MagicMock()
    entered_response = response.__enter__.return_value
    entered_response.headers = {}
    entered_response.read.side_effect = [b"1234", b"56"]
    opener = MagicMock(return_value=response)
    monkeypatch.setattr(cat_gif_generator.urllib.request, "urlopen", opener)

    assert (
        cat_gif_generator.fetch_cat_gif("https://cats.example/cat.gif", max_download_bytes=5)
        is None
    )
    assert entered_response.read.call_count == 2


def test_fetch_cat_gif_accepts_download_at_byte_limit(monkeypatch):
    """A response exactly at the byte budget remains valid."""
    response = MagicMock()
    entered_response = response.__enter__.return_value
    entered_response.headers = {}
    entered_response.read.side_effect = io.BytesIO(b"12345").read
    monkeypatch.setattr(
        cat_gif_generator.urllib.request, "urlopen", MagicMock(return_value=response)
    )

    assert (
        cat_gif_generator.fetch_cat_gif("https://cats.example/cat.gif", max_download_bytes=5)
        == b"12345"
    )
    assert [call.args for call in entered_response.read.call_args_list] == [(5,), (1,)]


def test_fetch_cat_gif_rejects_invalid_content_length(monkeypatch):
    """A malformed Content-Length is rejected without reading the response body."""
    response = MagicMock()
    entered_response = response.__enter__.return_value
    entered_response.headers = {"Content-Length": "not-a-number"}
    monkeypatch.setattr(
        cat_gif_generator.urllib.request, "urlopen", MagicMock(return_value=response)
    )

    assert cat_gif_generator.fetch_cat_gif("https://cats.example/cat.gif") is None
    entered_response.read.assert_not_called()


def test_extract_gif_frames_rejects_excessive_frame_count():
    """A GIF with too many frames is rejected rather than partially cached."""
    assert cat_gif_generator.extract_gif_frames(_gif_bytes(3), (2, 2), max_frames=2) == []


def test_extract_gif_frames_rejects_encoded_byte_limit():
    """Encoded JPEG frames cannot exceed their aggregate cache budget."""
    assert (
        cat_gif_generator.extract_gif_frames(_gif_bytes(), (32, 32), max_cached_jpeg_bytes=1) == []
    )


def test_failed_refresh_preserves_last_good_cache(monkeypatch):
    """Invalid replacement content does not discard previously cached frames."""
    generator = cat_gif_generator.CatGifGenerator("https://cats.example/cat.gif", (2, 2))
    original_frames = [(b"good jpeg", 0.1)]
    generator._frames = original_frames
    monkeypatch.setattr(cat_gif_generator, "fetch_cat_gif", lambda *args, **kwargs: b"bad")

    assert generator._fetch_and_cache_gif() is False
    assert generator._frames is original_frames


def test_cache_ttl_and_backoff_use_monotonic_clock(monkeypatch):
    """Expiry and retry deadlines are based only on the monotonic clock."""
    generator = cat_gif_generator.CatGifGenerator(
        "https://cats.example/cat.gif", (2, 2), cache_ttl_seconds=10, retry_base_seconds=3
    )
    monkeypatch.setattr(cat_gif_generator.time, "monotonic", MagicMock(return_value=100.0))
    monkeypatch.setattr(
        cat_gif_generator.time,
        "time",
        MagicMock(side_effect=AssertionError("wall clock must not be used")),
    )

    generator._fetch_time = 91.0
    assert generator._is_cache_expired() is False
    generator._fetch_time = 89.0
    assert generator._is_cache_expired() is True
    generator._record_fetch_failure()
    assert generator._next_retry_time == 103.0


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
