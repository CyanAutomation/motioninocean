"""Unit tests for mock stream frame rendering."""

import sys
from io import BytesIO

from PIL import Image

from pi_camera_in_docker import mock_stream_renderer


def test_render_mio_mock_frame_returns_jpeg_bytes(monkeypatch):
    """Renderer resizes the bundled raster asset and emits a JPEG without CairoSVG."""

    mock_stream_renderer.render_mio_mock_frame.cache_clear()
    mock_stream_renderer._load_mio_png_bytes.cache_clear()
    monkeypatch.setitem(sys.modules, "cairosvg", None)

    frame = mock_stream_renderer.render_mio_mock_frame(320, 240, 85)

    assert frame[:3] == b"\xff\xd8\xff"
    assert Image.open(BytesIO(frame)).size == (320, 240)
