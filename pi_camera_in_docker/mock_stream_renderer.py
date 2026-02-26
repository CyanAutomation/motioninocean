"""Render static mock stream frame bytes from the Mio SVG asset."""

from __future__ import annotations

from functools import lru_cache
from io import BytesIO
from pathlib import Path

from PIL import Image


class MockStreamRenderError(RuntimeError):
    """Raised when mock stream frame rendering cannot be completed."""


MSG_CAIROSVG_UNAVAILABLE = "cairosvg is unavailable for mock stream SVG rasterization"
MSG_RASTERIZE_FAILED = "Failed to rasterize and encode mock stream frame"


@lru_cache(maxsize=1)
def _load_mio_svg_bytes() -> bytes:
    """Load Mio SVG asset bytes from disk once per process.

    Returns:
        Raw SVG bytes loaded from static assets.

    Raises:
        MockStreamRenderError: If the SVG cannot be read.
    """
    svg_path = Path(__file__).resolve().parent / "static" / "img" / "mio" / "mio_mock_stream.svg"
    try:
        return svg_path.read_bytes()
    except OSError as exc:
        message = f"Failed to read mock stream SVG asset: {svg_path}"
        raise MockStreamRenderError(message) from exc


@lru_cache(maxsize=16)
def render_mio_mock_frame(width: int, height: int, jpeg_quality: int) -> bytes:
    """Render the Mio SVG asset into JPEG bytes at target output dimensions.

    Args:
        width: Output frame width in pixels.
        height: Output frame height in pixels.
        jpeg_quality: JPEG quality (1-100).

    Returns:
        Encoded JPEG bytes suitable for repeated frame buffer writes.

    Raises:
        MockStreamRenderError: If SVG rasterization or JPEG encoding fails.
    """
    if width <= 0 or height <= 0:
        message = f"Invalid target mock frame dimensions: {width}x{height}"
        raise MockStreamRenderError(message)

    try:
        import cairosvg  # noqa: PLC0415
    except (ModuleNotFoundError, OSError) as exc:
        raise MockStreamRenderError(MSG_CAIROSVG_UNAVAILABLE) from exc

    try:
        rasterized_png = cairosvg.svg2png(
            bytestring=_load_mio_svg_bytes(),
            output_width=width,
            output_height=height,
        )
        image = Image.open(BytesIO(rasterized_png)).convert("RGB")
        output = BytesIO()
        image.save(output, format="JPEG", quality=jpeg_quality)
        return output.getvalue()
    except Exception as exc:  # pragma: no cover - exact backend errors vary by platform
        raise MockStreamRenderError(MSG_RASTERIZE_FAILED) from exc
