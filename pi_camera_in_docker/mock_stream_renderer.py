"""Render mock stream JPEG frames from the bundled Mio raster artwork."""

from __future__ import annotations

from functools import lru_cache
from io import BytesIO
from pathlib import Path

from PIL import Image


class MockStreamRenderError(RuntimeError):
    """Raised when mock stream frame rendering cannot be completed."""


MSG_RENDER_FAILED = "Failed to resize and encode mock stream frame"


@lru_cache(maxsize=1)
def _load_mio_png_bytes() -> bytes:
    """Load the pre-rendered Mio PNG asset once per process.

    Returns:
        PNG bytes loaded from static assets.

    Raises:
        MockStreamRenderError: If the PNG cannot be read.
    """
    png_path = Path(__file__).resolve().parent / "static" / "img" / "mio" / "mio_mock_stream.png"
    try:
        return png_path.read_bytes()
    except OSError as exc:
        message = f"Failed to read mock stream PNG asset: {png_path}"
        raise MockStreamRenderError(message) from exc


@lru_cache(maxsize=16)
def render_mio_mock_frame(width: int, height: int, jpeg_quality: int) -> bytes:
    """Resize the Mio PNG asset and encode JPEG bytes at target dimensions.

    Args:
        width: Output frame width in pixels.
        height: Output frame height in pixels.
        jpeg_quality: JPEG quality (1-100).

    Returns:
        Encoded JPEG bytes suitable for repeated frame buffer writes.

    Raises:
        MockStreamRenderError: If the PNG cannot be read, resized, or encoded.
    """
    if width <= 0 or height <= 0:
        message = f"Invalid target mock frame dimensions: {width}x{height}"
        raise MockStreamRenderError(message)

    try:
        image = Image.open(BytesIO(_load_mio_png_bytes())).convert("RGB")
        image = image.resize((width, height), Image.Resampling.LANCZOS)
        output = BytesIO()
        image.save(output, format="JPEG", quality=jpeg_quality)
        return output.getvalue()
    except Exception as exc:  # pragma: no cover - exact backend errors vary by platform
        raise MockStreamRenderError(MSG_RENDER_FAILED) from exc
