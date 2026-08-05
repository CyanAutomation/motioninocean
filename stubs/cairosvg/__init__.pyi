"""Type stubs for cairosvg - SVG rendering library."""

from typing import Any, Optional, BinaryIO

def svg2png(
    bytestring: Optional[bytes] = None,
    file_obj: Optional[BinaryIO] = None,
    url: Optional[str] = None,
    write_to: Optional[BinaryIO] = None,
    output_width: Optional[int] = None,
    output_height: Optional[int] = None,
    **kwargs: Any
) -> Optional[bytes]: ...

def svg2pdf(
    bytestring: Optional[bytes] = None,
    file_obj: Optional[BinaryIO] = None,
    url: Optional[str] = None,
    write_to: Optional[BinaryIO] = None,
    **kwargs: Any
) -> Optional[bytes]: ...

def svg2ps(
    bytestring: Optional[bytes] = None,
    file_obj: Optional[BinaryIO] = None,
    url: Optional[str] = None,
    write_to: Optional[BinaryIO] = None,
    **kwargs: Any
) -> Optional[bytes]: ...
