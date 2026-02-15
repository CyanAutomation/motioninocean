"""
Unit tests for cat_gif_generator module.
Tests GIF fetching, frame extraction, caching, and frame generation.
"""

import io
import time
from unittest import mock

from PIL import Image


class TestFetchCatGif:
    """Test the fetch_cat_gif function."""

    def test_fetch_cat_gif_success(self):
        """Test successful GIF fetch."""
        from pi_camera_in_docker.cat_gif_generator import fetch_cat_gif

        # Create a minimal GIF
        gif_bytes = self._create_test_gif()

        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = mock.MagicMock()
            mock_response.read.return_value = gif_bytes
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            result = fetch_cat_gif("https://example.com/cat.gif")

            assert result == gif_bytes
            mock_urlopen.assert_called_once()

    def test_fetch_cat_gif_timeout(self):
        """Test GIF fetch with timeout."""
        from pi_camera_in_docker.cat_gif_generator import fetch_cat_gif

        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = TimeoutError("Connection timeout")

            result = fetch_cat_gif("https://example.com/cat.gif", timeout=5.0)

            assert result is None

    def test_fetch_cat_gif_http_error(self):
        """Test GIF fetch with HTTP error."""
        import urllib.error

        from pi_camera_in_docker.cat_gif_generator import fetch_cat_gif

        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.HTTPError("url", 404, "Not Found", {}, None)

            result = fetch_cat_gif("https://example.com/cat.gif")

            assert result is None

    def test_fetch_cat_gif_url_error(self):
        """Test GIF fetch with URL error."""
        import urllib.error

        from pi_camera_in_docker.cat_gif_generator import fetch_cat_gif

        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

            result = fetch_cat_gif("https://example.com/cat.gif")

            assert result is None

    @staticmethod
    def _create_test_gif() -> bytes:
        """Create a minimal GIF for testing."""
        img = Image.new("RGB", (100, 100), color="red")
        buf = io.BytesIO()
        img.save(buf, format="GIF")
        return buf.getvalue()


class TestExtractGifFrames:
    """Test the extract_gif_frames function."""

    def test_extract_single_frame_gif(self):
        """Test extracting frames from a single-frame GIF."""
        from pi_camera_in_docker.cat_gif_generator import extract_gif_frames

        gif_bytes = self._create_single_frame_gif()

        frames = extract_gif_frames(gif_bytes, (640, 480))

        assert len(frames) == 1
        assert isinstance(frames[0], tuple)
        assert len(frames[0]) == 2
        jpeg_bytes, duration = frames[0]
        assert isinstance(jpeg_bytes, bytes)
        assert isinstance(duration, float)
        assert duration > 0
        # Verify it's a valid JPEG
        assert jpeg_bytes[:2] == b"\xff\xd8"  # JPEG magic bytes

    def test_extract_animated_gif(self):
        """Test extracting frames from an animated GIF."""
        from pi_camera_in_docker.cat_gif_generator import extract_gif_frames

        gif_bytes = self._create_animated_gif(frame_count=5)

        frames = extract_gif_frames(gif_bytes, (640, 480))

        assert len(frames) == 5
        for jpeg_bytes, duration in frames:
            assert isinstance(jpeg_bytes, bytes)
            assert jpeg_bytes[:2] == b"\xff\xd8"  # JPEG magic
            assert isinstance(duration, float)
            assert duration > 0

    def test_extract_gif_frames_respects_resolution(self):
        """Test that extracted frames are resized correctly."""
        from pi_camera_in_docker.cat_gif_generator import extract_gif_frames

        gif_bytes = self._create_single_frame_gif(width=200, height=150)

        frames = extract_gif_frames(gif_bytes, resolution=(640, 480))

        # Verify by decoding the JPEG and checking dimensions
        assert len(frames) == 1
        jpeg_bytes, _ = frames[0]
        img = Image.open(io.BytesIO(jpeg_bytes))
        assert img.size == (640, 480)

    def test_extract_gif_frames_respects_quality(self):
        """Test that extracted frames respect JPEG quality setting."""
        from pi_camera_in_docker.cat_gif_generator import extract_gif_frames

        gif_bytes = self._create_single_frame_gif()

        # Extract with different qualities
        frames_high = extract_gif_frames(gif_bytes, (640, 480), jpeg_quality=95)
        frames_low = extract_gif_frames(gif_bytes, (640, 480), jpeg_quality=10)

        assert len(frames_high) == 1
        assert len(frames_low) == 1

        # Higher quality should generally produce larger files
        high_size = len(frames_high[0][0])
        low_size = len(frames_low[0][0])
        assert high_size > low_size

    def test_extract_gif_frames_invalid_data(self):
        """Test extracting frames from invalid GIF data."""
        from pi_camera_in_docker.cat_gif_generator import extract_gif_frames

        frames = extract_gif_frames(b"not a gif", (640, 480))

        assert frames == []

    def test_extract_gif_frames_empty_input(self):
        """Test extracting frames from empty input."""
        from pi_camera_in_docker.cat_gif_generator import extract_gif_frames

        frames = extract_gif_frames(b"", (640, 480))

        assert frames == []

    @staticmethod
    def _create_single_frame_gif(width: int = 100, height: int = 100) -> bytes:
        """Create a single-frame GIF for testing."""
        img = Image.new("RGB", (width, height), color="blue")
        buf = io.BytesIO()
        img.save(buf, format="GIF", duration=50)
        return buf.getvalue()

    @staticmethod
    def _create_animated_gif(frame_count: int = 3) -> bytes:
        """Create an animated GIF with multiple frames."""
        frames = []
        for i in range(frame_count):
            color = f"#{(i * 85) % 256:02x}{(i * 170) % 256:02x}{i * 50 % 256:02x}"
            img = Image.new("RGB", (100, 100), color=color)
            frames.append(img)

        buf = io.BytesIO()
        frames[0].save(
            buf,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            duration=100,
            loop=0,
        )
        return buf.getvalue()


class TestCatGifGenerator:
    """Test the CatGifGenerator class."""

    def test_initialization(self):
        """Test CatGifGenerator initialization."""
        from pi_camera_in_docker.cat_gif_generator import CatGifGenerator

        gen = CatGifGenerator(
            api_url="https://example.com/cat.gif",
            resolution=(640, 480),
            jpeg_quality=90,
            target_fps=10,
            cache_ttl_seconds=60.0,
        )

        assert gen.api_url == "https://example.com/cat.gif"
        assert gen.resolution == (640, 480)
        assert gen.jpeg_quality == 90
        assert gen.target_fps == 10
        assert gen.cache_ttl_seconds == 60.0

    def test_target_fps_minimum(self):
        """Test that target_fps is at least 1."""
        from pi_camera_in_docker.cat_gif_generator import CatGifGenerator

        gen = CatGifGenerator(
            api_url="https://example.com/cat.gif",
            resolution=(640, 480),
            target_fps=0,  # Invalid, should be corrected to 1
        )

        assert gen.target_fps == 1

    def test_request_refresh(self):
        """Test requesting a refresh."""
        from pi_camera_in_docker.cat_gif_generator import CatGifGenerator

        gen = CatGifGenerator(
            api_url="https://example.com/cat.gif",
            resolution=(640, 480),
        )

        # Initially, no refresh requested
        assert gen._refresh_requested is False

        gen.request_refresh()

        # After request, refresh flag should be set
        assert gen._refresh_requested is True

    def test_cache_expiration(self):
        """Test cache expiration logic."""
        from pi_camera_in_docker.cat_gif_generator import CatGifGenerator

        gen = CatGifGenerator(
            api_url="https://example.com/cat.gif",
            resolution=(640, 480),
            cache_ttl_seconds=1.0,  # 1 second TTL
        )

        # Initially expired (never fetched)
        assert gen._is_cache_expired() is True

        # Simulate a fetch
        gen._fetch_time = time.time()

        # Should not be expired immediately
        assert gen._is_cache_expired() is False

        # Wait for TTL to expire
        time.sleep(1.1)
        assert gen._is_cache_expired() is True

    def test_generate_frames_with_fallback(self):
        """Test frame generation with fallback on API failure."""
        from pi_camera_in_docker.cat_gif_generator import CatGifGenerator

        gen = CatGifGenerator(
            api_url="https://example.com/cat.gif",
            resolution=(640, 480),
        )

        with mock.patch.object(gen, "_fetch_and_cache_gif", return_value=False):
            frame_gen = gen.generate_frames()

            # Should yield fallback frame (black)
            for _ in range(3):
                frame = next(frame_gen)
                assert isinstance(frame, bytes)
                assert frame[:2] == b"\xff\xd8"  # JPEG magic

    def test_generate_frames_with_valid_gif(self):
        """Test frame generation with valid cached GIF."""
        from pi_camera_in_docker.cat_gif_generator import CatGifGenerator

        gif_bytes = self._create_test_gif()

        gen = CatGifGenerator(
            api_url="https://example.com/cat.gif",
            resolution=(640, 480),
            target_fps=30,  # 30 FPS
        )

        # Pre-populate frames
        from pi_camera_in_docker.cat_gif_generator import extract_gif_frames

        frames = extract_gif_frames(gif_bytes, (640, 480))
        gen._frames = frames
        gen._fetch_time = time.time()

        frame_gen = gen.generate_frames()

        # Should cycle through frames
        first_frame = next(frame_gen)
        assert isinstance(first_frame, bytes)
        assert first_frame[:2] == b"\xff\xd8"

    def test_generate_frames_refresh_request_honored(self):
        """Test that refresh requests trigger new fetch."""
        from pi_camera_in_docker.cat_gif_generator import CatGifGenerator

        gen = CatGifGenerator(
            api_url="https://example.com/cat.gif",
            resolution=(640, 480),
            cache_ttl_seconds=3600.0,  # Long TTL so it doesn't expire
        )

        # Pre-populate frames
        gen._frames = [(b"\xff\xd8\xff\xe0test", 0.1)]
        gen._fetch_time = time.time()

        fetch_called_count = 0

        def mock_fetch():
            nonlocal fetch_called_count
            fetch_called_count += 1
            return False

        with mock.patch.object(gen, "_fetch_and_cache_gif", side_effect=mock_fetch):
            frame_gen = gen.generate_frames()

            # First iteration calls initial fetch
            next(frame_gen)
            initial_fetch_count = fetch_called_count

            # Request refresh
            gen.request_refresh()

            # Next iteration should trigger fetch again
            next(frame_gen)
            assert fetch_called_count == initial_fetch_count + 1

    @staticmethod
    def _create_test_gif() -> bytes:
        """Create a test GIF."""
        img = Image.new("RGB", (100, 100), color="green")
        buf = io.BytesIO()
        img.save(buf, format="GIF")
        return buf.getvalue()


class TestCatGifGeneratorIntegration:
    """Integration tests for CatGifGenerator."""

    def test_full_workflow_with_mock_api(self):
        """Test full workflow with mocked API."""
        from pi_camera_in_docker.cat_gif_generator import CatGifGenerator

        gif_bytes = self._create_test_gif()

        gen = CatGifGenerator(
            api_url="https://cataas.com/cat.gif",
            resolution=(640, 480),
            target_fps=10,
            cache_ttl_seconds=1.0,
        )

        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = mock.MagicMock()
            mock_response.read.return_value = gif_bytes
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            frame_gen = gen.generate_frames()

            # Generate some frames
            frames = []
            for _ in range(5):
                frames.append(next(frame_gen))

            assert len(frames) == 5
            for frame in frames:
                assert isinstance(frame, bytes)
                assert frame[:2] == b"\xff\xd8"

    @staticmethod
    def _create_test_gif() -> bytes:
        """Create a test GIF."""
        img = Image.new("RGB", (100, 100), color="red")
        buf = io.BytesIO()
        img.save(buf, format="GIF")
        return buf.getvalue()
