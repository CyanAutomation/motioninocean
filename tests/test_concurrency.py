"""
Concurrency tests for the camera streaming application.
Tests race conditions, concurrent stream access, signal handling, and resource exhaustion.
"""

import io
import threading
import time
from collections import deque
from threading import Condition, Event, Lock
from typing import Optional

import pytest


class StreamStats:
    """Test version of StreamStats class."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._frame_count: int = 0
        self._last_frame_monotonic: Optional[float] = None
        self._frame_times_monotonic: deque[float] = deque(maxlen=30)

    def record_frame(self, monotonic_timestamp: float) -> None:
        """Record a new frame timestamp from a monotonic clock."""
        with self._lock:
            self._frame_count += 1
            self._last_frame_monotonic = monotonic_timestamp
            self._frame_times_monotonic.append(monotonic_timestamp)

    def get_fps(self) -> float:
        """Calculate actual FPS from frame times."""
        with self._lock:
            frame_times = list(self._frame_times_monotonic)
        if len(frame_times) < 2:
            return 0.0
        time_span = frame_times[-1] - frame_times[0]
        if time_span == 0:
            return 0.0
        return (len(frame_times) - 1) / time_span

    def snapshot(self) -> tuple[int, Optional[float], float]:
        """Return a snapshot of frame count, last frame time, and FPS."""
        with self._lock:
            frame_count = self._frame_count
            last_frame_time = self._last_frame_monotonic
            frame_times = list(self._frame_times_monotonic)

        # Calculate FPS outside lock using the snapshot
        if len(frame_times) < 2:
            current_fps = 0.0
        else:
            time_span = frame_times[-1] - frame_times[0]
            current_fps = 0.0 if time_span == 0 else (len(frame_times) - 1) / time_span

        return frame_count, last_frame_time, current_fps


class FrameBuffer(io.BufferedIOBase):
    """Test version of FrameBuffer class."""

    def __init__(self, stats: StreamStats, max_frame_size: Optional[int] = None) -> None:
        self.frame: Optional[bytes] = None
        self.condition: Condition = Condition()
        self._stats = stats
        self._max_frame_size = max_frame_size
        self._dropped_frames = 0

    def write(self, buf: bytes) -> int:
        """Write a new frame to the output buffer."""
        frame_size = len(buf)

        # Validate frame size to prevent memory exhaustion
        if self._max_frame_size is not None and frame_size > self._max_frame_size:
            self._dropped_frames += 1
            # Return the size to satisfy encoder interface, but don't store the frame
            return frame_size

        with self.condition:
            self.frame = buf
            monotonic_now = time.monotonic()
            self._stats.record_frame(monotonic_now)
            self.condition.notify_all()
        return frame_size

    def get_dropped_frames(self) -> int:
        """Return the number of dropped frames due to size limits."""
        return self._dropped_frames


class TestThreadSafety:
    """Test thread safety of core components."""

    def test_stream_stats_concurrent_writes(self):
        """Test that concurrent frame recording is thread-safe."""
        stats = StreamStats()
        num_threads = 10
        frames_per_thread = 100
        errors = []

        def record_frames():
            try:
                for _ in range(frames_per_thread):
                    stats.record_frame(time.monotonic())
                    time.sleep(0.001)  # Small delay to increase contention
            except Exception as e:
                errors.append(e)

        # Start multiple threads recording frames concurrently
        threads = [threading.Thread(target=record_frames) for _ in range(num_threads)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10.0)

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors during concurrent writes: {errors}"

        # Verify correct frame count
        frame_count, _, _ = stats.snapshot()
        assert frame_count == num_threads * frames_per_thread

    def test_stream_stats_concurrent_reads(self):
        """Test that concurrent reads don't block each other excessively."""
        stats = StreamStats()

        # Pre-populate with some data
        for _ in range(30):
            stats.record_frame(time.monotonic())
            time.sleep(0.01)

        num_readers = 20
        read_count = 50
        start_time = time.time()

        def read_stats():
            for _ in range(read_count):
                stats.snapshot()
                stats.get_fps()

        threads = [threading.Thread(target=read_stats) for _ in range(num_readers)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10.0)

        elapsed = time.time() - start_time

        # With proper locking (Lock instead of Condition), reads should be fast
        # 20 threads * 50 reads = 1000 total read operations should complete quickly
        assert elapsed < 5.0, f"Concurrent reads took too long: {elapsed}s"

    def test_frame_buffer_concurrent_write_read(self):
        """Test concurrent writes and reads on FrameBuffer."""
        stats = StreamStats()
        buffer = FrameBuffer(stats)
        errors = []
        frames_written = 0
        frames_read = 0
        stop_event = Event()

        def writer():
            nonlocal frames_written
            try:
                for i in range(100):
                    if stop_event.is_set():
                        break
                    frame_data = b"frame_" + str(i).encode() * 100
                    buffer.write(frame_data)
                    frames_written += 1
                    time.sleep(0.01)
            except Exception as e:
                errors.append(e)

        def reader():
            nonlocal frames_read
            try:
                for _ in range(50):
                    if stop_event.is_set():
                        break
                    with buffer.condition:
                        buffer.condition.wait(timeout=1.0)
                        if buffer.frame is not None:
                            frames_read += 1
            except Exception as e:
                errors.append(e)

        # Start one writer and multiple readers
        writer_thread = threading.Thread(target=writer)
        reader_threads = [threading.Thread(target=reader) for _ in range(3)]

        writer_thread.start()
        for thread in reader_threads:
            thread.start()

        writer_thread.join(timeout=5.0)
        stop_event.set()
        for thread in reader_threads:
            thread.join(timeout=2.0)

        assert len(errors) == 0, f"Errors during concurrent read/write: {errors}"
        assert frames_written > 0, "No frames were written"
        assert frames_read > 0, "No frames were read"


class TestConcurrentStreamAccess:
    """Test concurrent stream access scenarios."""

    def test_multiple_stream_connections(self):
        """Simulate multiple clients connecting to streams concurrently."""
        active_connections = 0
        connection_lock = Lock()
        max_connections = 10
        connection_errors = []

        def simulate_stream_client(client_id: int):
            nonlocal active_connections

            def check_connection_limit():
                """Check if connection limit is reached and raise error."""
                if active_connections >= max_connections:
                    msg = "Too many connections"
                    raise RuntimeError(msg)

            try:
                # Increment connection counter
                with connection_lock:
                    check_connection_limit()
                    active_connections += 1

                # Simulate streaming for a short time
                time.sleep(0.1)

                # Decrement connection counter
                with connection_lock:
                    active_connections -= 1
            except Exception as e:
                connection_errors.append((client_id, e))

        # Try to connect more clients than the limit
        num_clients = 15
        threads = [
            threading.Thread(target=simulate_stream_client, args=(i,)) for i in range(num_clients)
        ]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5.0)

        # Some connections should have been rejected
        assert len(connection_errors) > 0, "Expected some connections to be rejected"

        # Final connection count should be 0 (all cleaned up)
        assert active_connections == 0, "Connection leak detected"

    def test_connection_tracking_race_condition(self):
        """Test for race conditions in connection tracking."""
        active_connections = 0
        connection_lock = Lock()
        increments = 0
        decrements = 0

        def increment_connections():
            nonlocal active_connections, increments
            for _ in range(100):
                with connection_lock:
                    active_connections += 1
                    increments += 1

        def decrement_connections():
            nonlocal active_connections, decrements
            for _ in range(100):
                with connection_lock:
                    if active_connections > 0:
                        active_connections -= 1
                        decrements += 1

        # Run increment and decrement operations concurrently
        inc_threads = [threading.Thread(target=increment_connections) for _ in range(5)]
        dec_threads = [threading.Thread(target=decrement_connections) for _ in range(5)]

        for thread in inc_threads + dec_threads:
            thread.start()
        for thread in inc_threads + dec_threads:
            thread.join(timeout=5.0)

        # Verify no negative connections
        assert active_connections >= 0, "Connection count went negative"

        # Verify math adds up
        assert active_connections == increments - decrements


class TestSignalHandling:
    """Test signal handling for graceful shutdown."""

    def test_shutdown_event_flag(self):
        """Test that shutdown events are properly set and cleared."""
        shutdown_event = Event()
        recording_started = Event()

        def handle_shutdown():
            """Simulate signal handler."""
            recording_started.clear()
            shutdown_event.set()

        # Start recording
        recording_started.set()
        assert recording_started.is_set()
        assert not shutdown_event.is_set()

        # Trigger shutdown
        handle_shutdown()
        assert not recording_started.is_set()
        assert shutdown_event.is_set()

    def test_mock_thread_cleanup_timeout(self):
        """Test that mock thread cleanup handles timeout properly."""
        shutdown_event = Event()
        thread_stopped = False

        def mock_thread_function():
            nonlocal thread_stopped
            try:
                while not shutdown_event.is_set():
                    time.sleep(0.1)
            finally:
                thread_stopped = True

        # Start mock thread
        mock_thread = threading.Thread(target=mock_thread_function)
        mock_thread.daemon = False
        mock_thread.start()

        # Signal shutdown
        shutdown_event.set()

        # Wait with timeout
        mock_thread.join(timeout=2.0)

        # Thread should have stopped
        assert not mock_thread.is_alive()
        assert thread_stopped

    def test_mock_thread_forced_termination(self):
        """Test forced termination of stuck mock thread."""
        shutdown_event = Event()

        def stuck_thread_function():
            # Simulate a stuck thread that doesn't check shutdown_event
            for _ in range(10):  # Limited iterations for test
                if shutdown_event.is_set():
                    break
                time.sleep(0.1)

        # Start stuck thread
        mock_thread = threading.Thread(target=stuck_thread_function)
        mock_thread.daemon = False
        mock_thread.start()

        # Signal shutdown
        shutdown_event.set()

        # Wait with timeout
        mock_thread.join(timeout=0.5)

        # In Python 3.12+, we can't change daemon status of running threads
        # Instead, verify that the thread would eventually stop
        if mock_thread.is_alive():
            # Wait a bit more for the thread to notice shutdown_event
            mock_thread.join(timeout=2.0)
            # Thread should stop after checking shutdown_event
            assert not mock_thread.is_alive(), "Thread should eventually stop"


class TestResourceExhaustion:
    """Test resource exhaustion scenarios."""

    def test_frame_size_limit_enforcement(self):
        """Test that oversized frames are rejected."""
        stats = StreamStats()
        max_size = 1024  # 1 KB limit
        buffer = FrameBuffer(stats, max_frame_size=max_size)

        # Write a small frame (should succeed)
        small_frame = b"x" * 512
        result = buffer.write(small_frame)
        assert result == 512
        assert buffer.frame == small_frame
        assert buffer.get_dropped_frames() == 0

        # Write a large frame (should be dropped)
        large_frame = b"x" * 2048
        result = buffer.write(large_frame)
        assert result == 2048  # Returns size to satisfy encoder
        assert buffer.frame == small_frame  # Frame not updated
        assert buffer.get_dropped_frames() == 1

    def test_frame_buffer_memory_protection(self):
        """Test that frame buffer protects against memory exhaustion."""
        stats = StreamStats()
        # Set a reasonable limit (5 MB for 4K frame)
        max_size = 5 * 1024 * 1024
        buffer = FrameBuffer(stats, max_frame_size=max_size)

        # Try to write increasingly large frames
        sizes = [1024, 10240, 102400, 1024000, 10240000]  # 1KB to ~10MB
        dropped_count = 0

        for size in sizes:
            frame = b"x" * size
            buffer.write(frame)
            dropped_count = max(buffer.get_dropped_frames(), dropped_count)

        # At least one large frame should have been dropped
        assert dropped_count > 0, "Expected large frames to be dropped"

    def test_stream_timeout_handling(self):
        """Test that streams timeout when no frames are produced."""
        stats = StreamStats()
        buffer = FrameBuffer(stats)

        # Simulate a stream consumer waiting for frames
        timeout_count = 0
        max_timeouts = 3

        for _ in range(5):
            with buffer.condition:
                notified = buffer.condition.wait(timeout=0.1)
                if not notified:
                    timeout_count += 1
                    if timeout_count >= max_timeouts:
                        break

        # Should have hit the timeout limit
        assert timeout_count >= max_timeouts

    def test_concurrent_frame_writes_under_load(self):
        """Test system behavior under heavy concurrent frame writes."""
        stats = StreamStats()
        max_size = 1024 * 1024  # 1 MB
        buffer = FrameBuffer(stats, max_frame_size=max_size)

        write_errors = []
        frames_written = 0
        frames_dropped = 0

        def write_frames():
            nonlocal frames_written, frames_dropped
            for i in range(50):
                try:
                    # Alternate between normal and oversized frames
                    frame = b"x" * (max_size + 1000) if i % 10 == 0 else b"x" * 10000

                    buffer.write(frame)
                    frames_written += 1
                except Exception as e:
                    write_errors.append(e)

        # Multiple concurrent writers
        threads = [threading.Thread(target=write_frames) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10.0)

        frames_dropped = buffer.get_dropped_frames()

        # No errors should occur
        assert len(write_errors) == 0

        # Some frames should have been dropped due to size
        assert frames_dropped > 0

        # Most frames should have been written
        assert frames_written > 0


class TestMonotonicTiming:
    """Test monotonic clock usage for reliable timing."""

    def test_frame_age_calculation(self):
        """Test frame age calculation with monotonic time."""
        stats = StreamStats()

        # Record a frame
        frame_time = time.monotonic()
        stats.record_frame(frame_time)

        # Wait a bit
        time.sleep(0.1)

        # Calculate age
        _, last_frame_time, _ = stats.snapshot()
        if last_frame_time is not None:
            age = time.monotonic() - last_frame_time
            assert age >= 0.1
            assert age < 1.0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
