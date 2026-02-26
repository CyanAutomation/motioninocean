"""Unit tests for mock stream SVG rendering."""

import sys
import types

import pytest

from pi_camera_in_docker import mock_stream_renderer


def test_render_mio_mock_frame_returns_jpeg_bytes(monkeypatch):
    """Renderer should return JPEG bytes for requested dimensions and quality."""

    mock_stream_renderer.render_mio_mock_frame.cache_clear()
    mock_stream_renderer._load_mio_svg_bytes.cache_clear()

    def fake_svg2png(*, bytestring, output_width, output_height):
        assert bytestring
        assert output_width == 320
        assert output_height == 240
        return (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc``\xf8\xcf\xc0\x00\x00"
            b"\x03\x01\x01\x00\x18\xdd\x8d\xa5\x00\x00\x00\x00IEND\xaeB`\x82"
        )

    monkeypatch.setitem(sys.modules, "cairosvg", types.SimpleNamespace(svg2png=fake_svg2png))

    frame = mock_stream_renderer.render_mio_mock_frame(320, 240, 85)

    assert frame[:3] == b"\xff\xd8\xff"


def test_render_mio_mock_frame_raises_without_cairosvg(monkeypatch):
    """Renderer should raise MockStreamRenderError when cairosvg is unavailable."""

    mock_stream_renderer.render_mio_mock_frame.cache_clear()
    monkeypatch.delitem(sys.modules, "cairosvg", raising=False)

    original_import = __import__("builtins").__import__

    def fake_import(name, *args, **kwargs):
        if name == "cairosvg":
            raise ModuleNotFoundError("no module named cairosvg")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)

    with pytest.raises(mock_stream_renderer.MockStreamRenderError):
        mock_stream_renderer.render_mio_mock_frame(320, 240, 85)


def test_render_mio_mock_frame_raises_when_cairosvg_import_raises_oserror(monkeypatch):
    """Renderer should wrap cairosvg import OSError in MockStreamRenderError."""

    mock_stream_renderer.render_mio_mock_frame.cache_clear()
    monkeypatch.delitem(sys.modules, "cairosvg", raising=False)

    original_import = __import__("builtins").__import__

    def fake_import(name, *args, **kwargs):
        if name == "cairosvg":
            raise OSError("libcairo.so.2: cannot open shared object file: No such file or directory")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)

    with pytest.raises(mock_stream_renderer.MockStreamRenderError):
        mock_stream_renderer.render_mio_mock_frame(320, 240, 85)
