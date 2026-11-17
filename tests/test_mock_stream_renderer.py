"""Unit tests for mock stream frame rendering."""

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

from pi_camera_in_docker import mock_stream_renderer


def test_render_mio_mock_frame_matches_the_bundled_artwork():
    """Renderer emits the bundled mock artwork at the requested size."""

    mock_stream_renderer.render_mio_mock_frame.cache_clear()
    mock_stream_renderer._load_mio_png_bytes.cache_clear()

    width, height = 320, 240
    frame = mock_stream_renderer.render_mio_mock_frame(width, height, 85)
    rendered = Image.open(BytesIO(frame)).convert("RGB")
    artwork_path = (
        Path(mock_stream_renderer.__file__).parent
        / "static"
        / "img"
        / "mio"
        / "mio_mock_stream.png"
    )
    expected = (
        Image.open(artwork_path).convert("RGB").resize((width, height), Image.Resampling.LANCZOS)
    )
    mean_difference = ImageStat.Stat(ImageChops.difference(rendered, expected)).mean

    assert frame[:3] == b"\xff\xd8\xff"
    assert rendered.size == (width, height)
    assert sum(mean_difference) / 3 < 8
