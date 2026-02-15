"""
Cat GIF generator for mock camera mode.

Fetches animated GIFs from cataas.com API and streams individual JPEG frames
at a controlled frame rate. Supports frame extraction, caching, and graceful
fallback on API errors.
"""

import io
import logging
import threading
import time
import urllib.error
import urllib.request
from typing import Iterator, Optional, Tuple

from PIL import Image


logger = logging.getLogger(__name__)

# Default timeout for HTTP requests
REQUEST_TIMEOUT_SECONDS = 5.0


def fetch_cat_gif(api_url: str, timeout: float = REQUEST_TIMEOUT_SECONDS) -> Optional[bytes]:
    """
    Fetch a cat GIF from the cataas.com API.

    Args:
        api_url: The API endpoint URL (e.g., "https://cataas.com/cat.gif")
        timeout: Request timeout in seconds

    Returns:
        GIF file bytes if successful, None on error
    """
    try:
        with urllib.request.urlopen(api_url, timeout=timeout) as response:
            return response.read()
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        logger.warning(f"Failed to fetch cat GIF from {api_url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching cat GIF: {e}")
        return None


def extract_gif_frames(
    gif_bytes: bytes, resolution: Tuple[int, int], jpeg_quality: int = 90
) -> list[Tuple[bytes, float]]:
    """
    Extract all frames from an animated GIF and convert to JPEG buffers.

    Args:
        gif_bytes: Raw GIF file bytes
        resolution: Target resolution (width, height) for resizing frames
        jpeg_quality: JPEG quality (1-100)

    Returns:
        List of (jpeg_bytes, duration_seconds) tuples for each frame.
        If GIF parsing fails, returns empty list.
    """
    frames: list[Tuple[bytes, float]] = []

    try:
        gif_image = Image.open(io.BytesIO(gif_bytes))
        gif_image.load()

        # Check if this is actually an animated GIF
        frame_count = 1 if not hasattr(gif_image, "n_frames") else gif_image.n_frames

        for frame_idx in range(frame_count):
            try:
                gif_image.seek(frame_idx)
            except EOFError:
                logger.warning(f"Failed to seek to frame {frame_idx}")
                break

            # Get frame duration in milliseconds, default to 100ms
            duration_ms = gif_image.info.get("duration", 100)
            duration_seconds = duration_ms / 1000.0

            # Convert frame to RGB (in case of palette images)
            frame_rgb = gif_image.convert("RGB")

            # Resize to target resolution
            frame_resized = frame_rgb.resize(resolution, Image.Resampling.LANCZOS)

            # Encode to JPEG
            buf = io.BytesIO()
            frame_resized.save(buf, format="JPEG", quality=jpeg_quality)
            jpeg_bytes = buf.getvalue()

            frames.append((jpeg_bytes, duration_seconds))

        logger.info(f"Extracted {len(frames)} frames from cat GIF")
        return frames

    except Exception as e:
        logger.error(f"Failed to extract frames from GIF: {e}")
        return []


class CatGifGenerator:
    """
    Manages cat GIF fetching, frame extraction, caching, and streaming.

    Handles periodic updates, graceful degradation, and error recovery.
    Thread-safe frame generation for streaming to FrameBuffer.
    """

    def __init__(
        self,
        api_url: str,
        resolution: Tuple[int, int],
        jpeg_quality: int = 90,
        target_fps: int = 10,
        cache_ttl_seconds: float = 60.0,
    ):
        """
        Initialize the Cat GIF generator.

        Args:
            api_url: cataas.com API endpoint (e.g., "https://cataas.com/cat.gif")
            resolution: Target frame resolution (width, height)
            jpeg_quality: JPEG quality (1-100)
            target_fps: Desired frames per second for playback
            cache_ttl_seconds: How long to cache a GIF before fetching a new one
        """
        self.api_url = api_url
        self.resolution = resolution
        self.jpeg_quality = jpeg_quality
        self.target_fps = max(1, target_fps)  # At least 1 FPS
        self.cache_ttl_seconds = cache_ttl_seconds

        self._frames: list[Tuple[bytes, float]] = []
        self._fallback_frame: bytes = self._create_fallback_frame()
        self._fetch_time: Optional[float] = None
        self._lock = threading.Lock()
        self._refresh_requested = False
        self._frame_iteration_complete = False

    def _create_fallback_frame(self) -> bytes:
        """Create a black JPEG as fallback for API errors."""
        fallback = Image.new("RGB", self.resolution, color=(0, 0, 0))
        buf = io.BytesIO()
        fallback.save(buf, format="JPEG", quality=self.jpeg_quality)
        return buf.getvalue()

    def _is_cache_expired(self) -> bool:
        """Check if the current GIF cache has expired."""
        if self._fetch_time is None:
            return True
        return time.time() - self._fetch_time > self.cache_ttl_seconds

    def request_refresh(self) -> None:
        """Request a new cat GIF on the next frame iteration."""
        with self._lock:
            self._refresh_requested = True

    def _fetch_and_cache_gif(self) -> bool:
        """
        Fetch a new cat GIF and extract frames.

        Returns:
            True if successful, False on error (frames fall back to black)
        """
        logger.info(f"Fetching new cat GIF from {self.api_url}")
        gif_bytes = fetch_cat_gif(self.api_url)
        if gif_bytes is None:
            logger.warning("Failed to fetch cat GIF; using fallback frame")
            return False

        frames = extract_gif_frames(gif_bytes, self.resolution, self.jpeg_quality)
        if not frames:
            logger.warning("Failed to extract frames from cat GIF; using fallback frame")
            return False

        with self._lock:
            self._frames = frames
            self._fetch_time = time.time()
            self._refresh_requested = False

        return True

    def generate_frames(self) -> Iterator[bytes]:
        """
        Generate JPEG frame bytes, looping through cached GIF frames indefinitely.

        Yields:
            JPEG frame bytes

        Behavior:
            - Automatically fetches initial GIF if not cached
            - Respects cache TTL; refetches when expired or on explicit refresh request
            - Falls back to black frame if API errors occur
            - Respects frame timing from GIF and target_fps configuration
        """
        # Initial fetch
        self._fetch_and_cache_gif()

        frame_idx = 0

        while True:
            with self._lock:
                # Check if refresh was requested or cache expired
                if self._refresh_requested or self._is_cache_expired():
                    self._fetch_and_cache_gif()

                # Decide which frame to use
                if self._frames:
                    jpeg_bytes, frame_duration = self._frames[frame_idx]
                    current_frame_interval = frame_duration
                else:
                    # Fallback: use black frame at target FPS
                    jpeg_bytes = self._fallback_frame
                    current_frame_interval = 1.0 / self.target_fps

            yield jpeg_bytes

            # Advance frame index and loop
            with self._lock:
                if self._frames:
                    frame_idx = (frame_idx + 1) % len(self._frames)

            # Sleep respecting the frame's inherent timing
            time.sleep(current_frame_interval)
