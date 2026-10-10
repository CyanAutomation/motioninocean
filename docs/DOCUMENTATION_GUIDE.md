# Documentation Guide

Quick reference for documenting motion-in-ocean code. For complete examples and guidelines, see [AGENTS.md](https://github.com/CyanAutomation/motioninocean/blob/main/AGENTS.md#documentation-requirements) and [CONTRIBUTING.md](https://github.com/CyanAutomation/motioninocean/blob/main/CONTRIBUTING.md#documentation-standards).

---

## Python Documentation (Google-Style Docstrings)

### Module-Level Docstring

```python
"""Module for camera frame capture and streaming.

Handles frame acquisition from picamera2 hardware, JPEG encoding,
and integration with the streaming pipeline.
"""

import time
from typing import Optional
```

### Public Function

```python
def capture_frame(timeout_ms: Optional[int] = None) -> bytes:
    """Capture a single frame from camera.

    Acquires a frame from the camera hardware via picamera2 and encodes
    to JPEG format at the configured quality setting.

    Args:
        timeout_ms: Maximum wait time in milliseconds. If None, uses default
            from application settings. Must be greater than 0.

    Returns:
        JPEG-encoded frame bytes ready for streaming.

    Raises:
        RuntimeError: If camera is not initialized or frame capture fails.
        TimeoutError: If frame not ready within timeout_ms.
    """
    # Implementation
```

### Public Class

```python
class FrameBuffer:
    """Thread-safe circular buffer for storing camera frames.

    Manages frame acquisition, rotation, and access across streaming threads
    without dropping frames during high load.

    Attributes:
        max_size: Maximum number of frames to buffer. Defaults to 10.
        timeout_ms: Frame access timeout in milliseconds.
    """

    def __init__(self, max_size: int = 10, timeout_ms: int = 100):
        """Initialize buffer with specified capacity.

        Args:
            max_size: Maximum frames to hold. Must be >= 1.
            timeout_ms: Max wait time for frame availability.

        Raises:
            ValueError: If max_size < 1 or timeout_ms < 0.
        """
        self.max_size = max_size
        self.timeout_ms = timeout_ms

    def get_latest(self) -> bytes:
        """Get the most recent frame in buffer.

        Returns:
            JPEG-encoded frame bytes.

        Raises:
            TimeoutError: If no frame available within timeout_ms.
            RuntimeError: If buffer is not initialized.
        """
        # Implementation
```

### Private Function (> 5 LOC)

```python
def _process_frame_metadata(frame: bytes, timestamp: float) -> dict:
    """Extract and cache frame metadata for monitoring.

    Internal helper for recording frame statistics like size, encoding time,
    and timestamp for health checks and monitoring.

    Args:
        frame: JPEG-encoded frame bytes.
        timestamp: Unix timestamp when frame was captured.

    Returns:
        Dictionary with keys: size_bytes, captured_at, encoder_version.
    """
    # Implementation
```

### REST Endpoint (GET)

```python
@app.route("/api/status", methods=["GET"])
def get_status() -> dict:
    """Get current stream status and server health.

    Returns stream availability, connected client count, frame rate,
    and any degradation warnings.

    Authentication:
        Requires bearer token in Authorization header.

    Returns:
        JSON object with keys: status, stream_available, clients_connected,
        fps, error_message (if degraded).

    Status Codes:
        200: Stream is operational.
        503: Camera initialization failed or hardware unavailable.
    """
    # Implementation
```

### REST Endpoint (PATCH)

```python
@app.route("/api/settings", methods=["PATCH"])
def update_settings() -> dict:
    """Update runtime settings with validation and persistence.

    Accepts partial settings update, validates against schema, applies
    immediately, and persists to /data/application-settings.json.

    Request Body:
        JSON object with camera, streaming, or other setting branches.
        Example: {"camera": {"resolution": "1280x720"}}

    Authentication:
        Requires bearer token in Authorization header.

    Returns:
        Updated settings object after validation and persistence.

    Raises:
        400: Invalid setting value or schema violation.
        401: Missing or invalid authentication token.
        409: Conflict with current state (e.g., setting immutable during capture).

    Examples:
        PATCH /api/settings HTTP/1.1
        Authorization: Bearer <token>
        Content-Type: application/json

        {"camera": {"fps": 30}}
    """
    # Implementation
```

---

## Frontend TypeScript Documentation

Frontend behavior is authored in `frontend/src/` and compiled to browser JavaScript in
`pi_camera_in_docker/static/js/`. Put parameter and return types in TypeScript signatures;
use JSDoc for purpose, behavior, side effects, and errors. `make jsdoc` builds the generated
API reference from the compiled files.

```typescript
/**
 * Fetch stream metadata from a remote node.
 *
 * Uses bearer-token authentication and retries transient network failures.
 *
 * @throws {Error} If the node is unreachable or rejects authentication.
 */
async function fetchNodeStatus(
  nodeId: string,
  baseUrl: string,
  authToken: string,
): Promise<NodeStatus> {
  // Implementation
}
```

---

## Common Patterns

### Python: Async/Await with Error Handling

```python
async def stream_frames(timeout_ms: int = 5000) -> None:
    """Stream frames indefinitely with error recovery.

    Captures frames in a loop, handles transient camera errors,
    and logs degradation for monitoring.

    Args:
        timeout_ms: Max wait per frame capture.

    Raises:
        CameraInitError: If camera unavailable at startup.

    Note:
        Long-running async task. Call in separate thread or event loop.
    """
    # Implementation
```

### Python: Optional Parameters with Defaults

```python
def configure_stream(
    resolution: str = "640x480",
    fps: int = 24,
    quality: int = 90,
    retry_count: Optional[int] = None,
) -> StreamConfig:
    """Configure camera stream with defaults.

    Args:
        resolution: Output resolution. Defaults to "640x480".
        fps: Frames per second. Defaults to 24. Must be 1-120.
        quality: JPEG quality (1-100). Defaults to 90.
        retry_count: Retry attempts on transient errors. If None, uses
            environment default from STREAM_MAX_RETRIES.

    Returns:
        StreamConfig object ready for initialization.

    Raises:
        ValueError: If fps or quality out of valid range.
    """
    # Implementation
```

### TypeScript: Async with Retry

```typescript
/**
 * Fetch data with exponential backoff retry.
 *
 * Implements standard retry pattern with jitter to prevent
 * thundering herd on recovery.
 *
 * @throws {Error} If max retries exceeded
 */
async function fetchWithRetry(url: string, maxRetries = 3): Promise<Response> {
  // Implementation
}
```

### TypeScript: Error Handling

```typescript
/**
 * Display error message to user with automatic dismissal.
 *
 * Shows transient errors for 5 seconds, persistent errors require
 * manual dismissal. Logs errors for debugging.
 *
 * @throws {TypeError} If error not Error or string
 */
function showError(error: Error | string, timeoutMs = 5000): void {
  // Implementation
}
```

---

## Validation Commands

Before pushing, validate documentation builds locally:

```bash
# Check if documentation builds without warnings/errors (CI validation)
make docs-check

# Build full Sphinx HTML documentation
make docs-build

# Build API docs from TypeScript JSDoc comments
make jsdoc
# Clean generated docs
make docs-clean
```

---

## Quick Checklist

When documenting new functions/classes:

- [ ] **Python**: Google-style docstring with Args, Returns, Raises, Examples (if needed)
- [ ] **Python private functions > 5 LOC**: Include docstring explaining purpose
- [ ] **TypeScript**: Explicit parameter and return types; JSDoc describes purpose and behavior
- [ ] **Private TypeScript functions > 10 LOC**: Include a doc comment explaining purpose
- [ ] **Classes**: Document constructor and all public methods
- [ ] **Modules**: Add module-level docstring with purpose and scope
- [ ] **REST endpoints**: Document request body, response format, status codes, authentication
- [ ] **Complex logic**: Include Notes or Examples section for clarity
- [ ] **Run validation**: `make docs-check` and `make jsdoc` pass before commit

---

## References

- [PEP 257 — Docstring Conventions](https://peps.python.org/pep-0257/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
- [JSDoc Documentation](https://jsdoc.app/)
- [AGENTS.md#documentation-requirements](https://github.com/CyanAutomation/motioninocean/blob/main/AGENTS.md#documentation-requirements) — Full guidelines
- [CONTRIBUTING.md#documentation-standards](https://github.com/CyanAutomation/motioninocean/blob/main/CONTRIBUTING.md#documentation-standards) — Contribution requirements
