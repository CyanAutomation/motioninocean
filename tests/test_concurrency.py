"""Behavioral concurrency tests for webcam streaming components."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Condition, Event, Lock, Thread

from pi_camera_in_docker.modes.webcam import ConnectionTracker, FrameBuffer, StreamStats


def test_stream_stats_counts_every_frame_from_concurrent_writers() -> None:
    """Concurrent writes preserve exact frame counts.

    Traceability: docs/product/PRD-backend.md#1-mjpeg-streaming-endpoint-p1.
    """
    worker_count = 8
    frames_per_worker = 250
    stats = StreamStats()
    start = Barrier(worker_count)

    def record_frames(worker_id: int) -> None:
        start.wait(timeout=5)
        for frame_index in range(frames_per_worker):
            stats.record_frame(float(worker_id * frames_per_worker + frame_index))

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [executor.submit(record_frames, worker_id) for worker_id in range(worker_count)]
        for future in futures:
            future.result()

    frame_count, last_timestamp, _current_fps = stats.snapshot()

    assert frame_count == worker_count * frames_per_worker
    assert last_timestamp is not None


def test_stream_stats_snapshots_remain_consistent_during_writes() -> None:
    """Snapshots pair counts and timestamps during concurrent writes.

    Traceability: docs/product/PRD-backend.md#1-mjpeg-streaming-endpoint-p1.
    """
    writer_count = 4
    reader_count = 4
    writes_per_worker = 200
    total_writes = writer_count * writes_per_worker
    stats = StreamStats()
    start = Barrier(writer_count + reader_count)

    def record_frames(worker_id: int) -> None:
        start.wait(timeout=5)
        for frame_index in range(writes_per_worker):
            stats.record_frame(float(worker_id * writes_per_worker + frame_index))

    def read_snapshots() -> None:
        start.wait(timeout=5)
        for _ in range(300):
            frame_count, last_timestamp, _current_fps = stats.snapshot()
            assert 0 <= frame_count <= total_writes
            assert (last_timestamp is None) is (frame_count == 0)

    with ThreadPoolExecutor(max_workers=writer_count + reader_count) as executor:
        futures = [executor.submit(record_frames, worker_id) for worker_id in range(writer_count)]
        futures.extend(executor.submit(read_snapshots) for _ in range(reader_count))
        for future in futures:
            future.result()

    assert stats.snapshot()[0] == total_writes


def test_frame_buffer_wakes_waiting_readers_with_a_published_frame() -> None:
    """A write notifies readers blocked on the frame buffer.

    Traceability: docs/product/PRD-backend.md#1-mjpeg-streaming-endpoint-p1.
    """
    reader_count = 4
    stats = StreamStats()
    output = FrameBuffer(stats)
    waiting_readers = Event()
    received_frames: list[bytes | None] = []
    frame = b"jpeg-frame"

    class ReaderTrackingCondition(Condition):
        def __init__(self) -> None:
            super().__init__()
            self._reader_count = 0
            self._reader_count_lock = Lock()

        def wait(self, timeout: float | None = None) -> bool:
            with self._reader_count_lock:
                self._reader_count += 1
                if self._reader_count == reader_count:
                    waiting_readers.set()
            return super().wait(timeout)

    output.condition = ReaderTrackingCondition()

    def read_frame() -> None:
        with output.condition:
            assert output.condition.wait(timeout=5)
            received_frames.append(output.frame)

    with ThreadPoolExecutor(max_workers=reader_count) as executor:
        futures = [executor.submit(read_frame) for _ in range(reader_count)]
        assert waiting_readers.wait(timeout=5)
        output.write(frame)
        for future in futures:
            future.result()

    assert received_frames == [frame] * reader_count
    assert stats.snapshot()[0] == 1


def test_connection_tracker_enforces_limit_for_simultaneous_clients() -> None:
    """The tracker admits no more than the configured client limit.

    Traceability: docs/product/PRD-backend.md#1-mjpeg-streaming-endpoint-p1.
    """
    max_connections = 10
    client_count = 20
    tracker = ConnectionTracker()
    start = Barrier(client_count)

    def try_connect() -> bool:
        start.wait(timeout=5)
        return tracker.try_increment(max_connections)

    with ThreadPoolExecutor(max_workers=client_count) as executor:
        admitted = list(executor.map(lambda _client: try_connect(), range(client_count)))

    assert sum(admitted) == max_connections
    assert tracker.get_count() == max_connections
    for _ in range(max_connections):
        tracker.decrement()
    assert tracker.get_count() == 0


def test_frame_buffer_skips_oversized_frames_without_changing_stream_state() -> None:
    """Oversized frames are dropped without replacing the last valid frame.

    Traceability: docs/product/PRD-backend.md#1-mjpeg-streaming-endpoint-p1.
    """
    max_frame_size = 1024
    stats = StreamStats()
    output = FrameBuffer(stats, max_frame_size=max_frame_size)
    accepted_frame = b"a" * max_frame_size
    oversized_frame = b"b" * (max_frame_size + 1)

    assert output.write(accepted_frame) == max_frame_size
    before_oversized_write = stats.snapshot()
    assert output.frame == accepted_frame

    assert output.write(oversized_frame) == len(oversized_frame)
    assert output.frame == accepted_frame
    assert stats.snapshot() == before_oversized_write


def test_concurrent_frame_buffer_writes_publish_a_complete_frame() -> None:
    """Concurrent writes publish whole frames and count each accepted write.

    Traceability: docs/product/PRD-backend.md#1-mjpeg-streaming-endpoint-p1.
    """
    writer_count = 8
    writes_per_worker = 100
    stats = StreamStats()
    output = FrameBuffer(stats)
    start = Barrier(writer_count)
    expected_frames = {
        f"worker-{worker_id}-frame-{frame_index}".encode()
        for worker_id in range(writer_count)
        for frame_index in range(writes_per_worker)
    }

    def write_frames(worker_id: int) -> None:
        start.wait(timeout=5)
        for frame_index in range(writes_per_worker):
            output.write(f"worker-{worker_id}-frame-{frame_index}".encode())

    with ThreadPoolExecutor(max_workers=writer_count) as executor:
        futures = [executor.submit(write_frames, worker_id) for worker_id in range(writer_count)]
        for future in futures:
            future.result()

    assert output.frame in expected_frames
    assert stats.snapshot()[0] == writer_count * writes_per_worker


def test_synthetic_frame_worker_stops_after_shutdown_is_requested(monkeypatch) -> None:
    """The synthetic frame worker exits and clears its running state on shutdown.

    Traceability: docs/product/PRD-backend.md#6-mock-camera-mode-p3.
    """
    from pi_camera_in_docker import main

    recording_started = Event()
    shutdown_requested = Event()
    first_frame_written = Event()
    written_frames: list[bytes] = []
    workers: list[Thread] = []
    real_thread = Thread

    class OutputStub:
        def write(self, frame: bytes) -> int:
            written_frames.append(frame)
            first_frame_written.set()
            return len(frame)

    def capture_worker(*args, **kwargs) -> Thread:
        worker = real_thread(*args, **kwargs)
        workers.append(worker)
        return worker

    frame = b"\xff\xd8mock-jpeg"
    monkeypatch.setattr(main, "render_mio_mock_frame", lambda *_args: frame)
    monkeypatch.setattr(main, "Thread", capture_worker)
    state = {
        "recording_started": recording_started,
        "shutdown_requested": shutdown_requested,
        "output": OutputStub(),
    }

    main._init_mock_camera_frames(
        state,
        {"resolution": (640, 480), "jpeg_quality": 85, "fps": 1000},
    )
    worker = workers[0]

    try:
        assert recording_started.wait(timeout=2)
        assert first_frame_written.wait(timeout=2)
    finally:
        shutdown_requested.set()
        worker.join(timeout=2)

    assert not worker.is_alive()
    assert not recording_started.is_set()
    assert written_frames
    assert written_frames[0] == frame
