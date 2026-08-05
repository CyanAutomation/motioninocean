"""Type stubs for picamera2.outputs."""

from typing import Any, Optional, BinaryIO

class FileOutput:
    """File output for encoded video."""
    
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

class StreamOutput:
    """Stream output for encoded video."""
    
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

class FdOutput:
    """File descriptor output."""
    
    def __init__(self, fd: int, *args: Any, **kwargs: Any) -> None: ...
