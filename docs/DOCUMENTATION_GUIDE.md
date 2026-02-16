# Documentation Guide

Quick reference for documenting motion-in-ocean code. For complete examples and guidelines, see [AGENTS.md](../AGENTS.md#documentation-requirements) and [CONTRIBUTING.md](../CONTRIBUTING.md#documentation-standards).

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

## JavaScript Documentation (JSDoc)

### Module Header

```javascript
/**
 * Streaming viewer for motion-in-ocean webcam.
 *
 * Handles video stream display, connection state management,
 * and real-time frame rate/ status monitoring.
 *
 * @module app
 */
```

### Async Function

```javascript
/**
 * Fetch stream metadata from remote node.
 *
 * Queries /api/status endpoint with bearer token authentication.
 * Includes automatic retry with exponential backoff on network errors.
 *
 * @param {string} nodeId - Unique node identifier
 * @param {string} baseUrl - Node base URL (http[s]://host:port)
 * @param {string} authToken - Bearer token for authentication
 * @returns {Promise<Object>} Node status object with keys:
 *   status (string), stream_available (boolean), fps (number)
 * @throws {Error} If node unreachable after retries or auth fails
 * @async
 */
async function fetchNodeStatus(nodeId, baseUrl, authToken) {
  // Implementation
}
```

### Synchronous Function

```javascript
/**
 * Parse MJPEG content-type header and extract boundary.
 *
 * Extracts the multipart boundary string from MJPEG stream
 * headers for frame separation and decoding.
 *
 * @param {string} contentType - HTTP Content-Type header value
 * @returns {string} Multipart boundary string (e.g., "frame")
 * @throws {Error} If boundary not found in content-type
 */
function extractMjpegBoundary(contentType) {
  // Implementation
}
```

### Class / IIFE Pattern

```javascript
/**
 * Manage WebSocket connection to streaming server.
 *
 * Wraps native WebSocket with exponential backoff reconnection,
 * message buffering, and automatic cleanup on disconnect.
 *
 * @class StreamConnection
 *
 * @example
 * const conn = new StreamConnection(
 *   "ws://localhost:8000/stream",
 *   {auth_token: "abc123", max_retries: 5}
 * );
 * conn.onFrame = (frame) => displayImage(frame);
 * conn.connect();
 */
class StreamConnection {
  /**
   * Create a new streaming connection.
   *
   * @param {string} wsUrl - WebSocket server URL
   * @param {Object} options - Configuration options
   * @param {string} options.auth_token - Bearer token for authentication
   * @param {number} options.max_retries - Maximum reconnection attempts
   * @param {number} options.backoff_ms - Initial backoff in milliseconds
   *
   * @throws {TypeError} If wsUrl is not a valid URL string
   */
  constructor(wsUrl, options = {}) {
    // Implementation
  }

  /**
   * Establish connection to server and start receiving frames.
   *
   * Returns immediately; connection is asynchronous.
   * Emits 'connected' event when ready, 'error' on failure.
   *
   * @returns {Promise<void>} Resolves when first frame received
   * @throws {Error} If max_retries exceeded
   * @async
   */
  async connect() {
    // Implementation
  }
}
```

### Private Function (> 10 LOC)

```javascript
/**
 * Parse raw MJPEG frame boundary and extract image data.
 *
 * Internal helper for decoding MJPEG multipart boundaries and
 * extracting individual JPEG frame bytes from stream.
 * Not for external use; subject to change.
 *
 * @private
 * @param {Uint8Array} buffer - Raw stream buffer
 * @param {string} boundary - Multipart boundary marker
 * @returns {Object} Extracted frame with keys: data (Uint8Array), size
 * @throws {Error} If boundary not found in buffer
 */
function _decodeFrameFromBuffer(buffer, boundary) {
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

### JavaScript: Async with Retry

```javascript
/**
 * Fetch data with exponential backoff retry.
 *
 * Implements standard retry pattern with jitter to prevent
 * thundering herd on recovery.
 *
 * @param {string} url - HTTP endpoint
 * @param {number} maxRetries - Maximum attempts (default 3)
 * @returns {Promise<Response>} Fetch response object
 * @throws {Error} If max retries exceeded
 * @async
 */
async function fetchWithRetry(url, maxRetries = 3) {
  // Implementation
}
```

### JavaScript: Error Handling

```javascript
/**
 * Display error message to user with automatic dismissal.
 *
 * Shows transient errors for 5 seconds, persistent errors require
 * manual dismissal. Logs errors for debugging.
 *
 * @param {Error} error - Error object or message string
 * @param {number} timeout_ms - Auto-dismiss timeout in ms (0 = never)
 * @throws {TypeError} If error not Error or string
 */
function showError(error, timeout_ms = 5000) {
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

# Build JSDoc for JavaScript files
make jsdoc

# Clean generated docs
make docs-clean
```

---

## Quick Checklist

When documenting new functions/classes:

- [ ] **Python**: Google-style docstring with Args, Returns, Raises, Examples (if needed)
- [ ] **Python private functions > 5 LOC**: Include docstring explaining purpose
- [ ] **JavaScript**: JSDoc header with @param, @returns, @throws, @async (if applicable)
- [ ] **JavaScript private functions > 10 LOC**: Include docstring with @private tag
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
- [AGENTS.md#documentation-requirements](../AGENTS.md#documentation-requirements) — Full guidelines
- [CONTRIBUTING.md#documentation-standards](../CONTRIBUTING.md#documentation-standards) — Contribution requirements
