"""Type stubs for picamera2.encoders."""

from typing import Any, Optional

class MJPEGEncoder:
    """MJPEG encoder for video streaming."""
    
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

class H264Encoder:
    """H.264 video encoder."""
    
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

class JpegEncoder:
    """JPEG still image encoder."""
    
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...
