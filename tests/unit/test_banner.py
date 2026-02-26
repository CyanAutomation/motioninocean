"""Unit tests for pi_camera_in_docker.banner."""

from pi_camera_in_docker.banner import MIO_ASCII, _read_app_version, print_startup_banner


# ---------------------------------------------------------------------------
# _read_app_version helper
# ---------------------------------------------------------------------------


def test_read_app_version_returns_string_from_file(tmp_path, monkeypatch) -> None:
    """_read_app_version reads the version from the first resolvable VERSION file."""
    version_file = tmp_path / "VERSION"
    version_file.write_text("9.8.7\n", encoding="utf-8")

    import pi_camera_in_docker.banner as banner_module

    original_candidates = banner_module._VERSION_FILE_CANDIDATES
    monkeypatch.setattr(banner_module, "_VERSION_FILE_CANDIDATES", [version_file])
    try:
        result = _read_app_version()
    finally:
        monkeypatch.setattr(banner_module, "_VERSION_FILE_CANDIDATES", original_candidates)

    assert result == "9.8.7"


def test_read_app_version_returns_unknown_when_no_file(monkeypatch, tmp_path) -> None:
    """_read_app_version returns 'unknown' when no VERSION file exists."""
    import pi_camera_in_docker.banner as banner_module

    original_candidates = banner_module._VERSION_FILE_CANDIDATES
    monkeypatch.setattr(banner_module, "_VERSION_FILE_CANDIDATES", [tmp_path / "MISSING"])
    try:
        result = _read_app_version()
    finally:
        monkeypatch.setattr(banner_module, "_VERSION_FILE_CANDIDATES", original_candidates)

    assert result == "unknown"


# ---------------------------------------------------------------------------
# print_startup_banner — text mode
# ---------------------------------------------------------------------------


def test_banner_text_mode_writes_to_stderr(capsys, monkeypatch) -> None:
    """Banner writes to stderr, not stdout, in text mode."""
    monkeypatch.delenv("MIO_LOG_FORMAT", raising=False)

    print_startup_banner("webcam", "127.0.0.1", 8000, version="1.0.0")

    captured = capsys.readouterr()
    assert captured.out == ""
    assert len(captured.err) > 0


def test_banner_text_mode_contains_version(capsys, monkeypatch) -> None:
    """Banner output includes the supplied version string in text mode."""
    monkeypatch.setenv("MIO_LOG_FORMAT", "text")

    print_startup_banner("webcam", "127.0.0.1", 8000, version="2.3.4")

    captured = capsys.readouterr()
    assert "2.3.4" in captured.err


def test_banner_text_mode_contains_mode(capsys, monkeypatch) -> None:
    """Banner output includes the mode in text mode."""
    monkeypatch.setenv("MIO_LOG_FORMAT", "text")

    print_startup_banner("management", "0.0.0.0", 8001, version="1.0.0")

    captured = capsys.readouterr()
    assert "management" in captured.err


def test_banner_text_mode_contains_address(capsys, monkeypatch) -> None:
    """Banner output includes the bind address and port in text mode."""
    monkeypatch.setenv("MIO_LOG_FORMAT", "text")

    print_startup_banner("webcam", "0.0.0.0", 8000, version="1.0.0")

    captured = capsys.readouterr()
    assert "0.0.0.0:8000" in captured.err


def test_banner_text_mode_contains_repo_url(capsys, monkeypatch) -> None:
    """Banner output includes the GitHub repository URL in text mode."""
    monkeypatch.setenv("MIO_LOG_FORMAT", "text")

    print_startup_banner("webcam", "127.0.0.1", 8000, version="1.0.0")

    captured = capsys.readouterr()
    assert "github.com/CyanAutomation/motioninocean" in captured.err


def test_banner_text_mode_contains_ascii_art(capsys, monkeypatch) -> None:
    """Banner output includes at least part of the ASCII art in text mode."""
    monkeypatch.setenv("MIO_LOG_FORMAT", "text")

    print_startup_banner("webcam", "127.0.0.1", 8000, version="1.0.0")

    captured = capsys.readouterr()
    # The ASCII art block must be present (check for a distinctive line)
    assert MIO_ASCII.strip()[:10] in captured.err


def test_banner_text_mode_is_multiline(capsys, monkeypatch) -> None:
    """Banner output is multi-line in text mode (not a single compact line)."""
    monkeypatch.setenv("MIO_LOG_FORMAT", "text")

    print_startup_banner("webcam", "127.0.0.1", 8000, version="1.0.0")

    captured = capsys.readouterr()
    assert captured.err.count("\n") >= 5


# ---------------------------------------------------------------------------
# print_startup_banner — JSON mode
# ---------------------------------------------------------------------------


def test_banner_json_mode_writes_to_stderr(capsys, monkeypatch) -> None:
    """Compact fallback writes to stderr, not stdout, in JSON mode."""
    monkeypatch.setenv("MIO_LOG_FORMAT", "json")

    print_startup_banner("webcam", "127.0.0.1", 8000, version="1.0.0")

    captured = capsys.readouterr()
    assert captured.out == ""
    assert len(captured.err.strip()) > 0


def test_banner_json_mode_is_single_line(capsys, monkeypatch) -> None:
    """Compact fallback must be a single line in JSON mode."""
    monkeypatch.setenv("MIO_LOG_FORMAT", "json")

    print_startup_banner("webcam", "127.0.0.1", 8000, version="1.0.0")

    captured = capsys.readouterr()
    # Strip trailing newline then check for no embedded newlines
    assert "\n" not in captured.err.strip()


def test_banner_json_mode_contains_version(capsys, monkeypatch) -> None:
    """Compact fallback includes the version string in JSON mode."""
    monkeypatch.setenv("MIO_LOG_FORMAT", "json")

    print_startup_banner("webcam", "127.0.0.1", 8000, version="5.6.7")

    captured = capsys.readouterr()
    assert "5.6.7" in captured.err


def test_banner_json_mode_contains_mode(capsys, monkeypatch) -> None:
    """Compact fallback includes the mode in JSON mode."""
    monkeypatch.setenv("MIO_LOG_FORMAT", "json")

    print_startup_banner("management", "0.0.0.0", 8001, version="1.0.0")

    captured = capsys.readouterr()
    assert "management" in captured.err


def test_banner_json_mode_contains_address(capsys, monkeypatch) -> None:
    """Compact fallback includes the bind address and port in JSON mode."""
    monkeypatch.setenv("MIO_LOG_FORMAT", "json")

    print_startup_banner("webcam", "0.0.0.0", 9000, version="1.0.0")

    captured = capsys.readouterr()
    assert "0.0.0.0:9000" in captured.err


def test_banner_json_mode_no_ascii_art(capsys, monkeypatch) -> None:
    """Compact fallback must NOT contain multi-line ASCII art in JSON mode."""
    monkeypatch.setenv("MIO_LOG_FORMAT", "json")

    print_startup_banner("webcam", "127.0.0.1", 8000, version="1.0.0")

    captured = capsys.readouterr()
    # The ASCII art body should not be present in JSON mode output
    assert MIO_ASCII.strip()[:10] not in captured.err


def test_banner_json_mode_case_insensitive(capsys, monkeypatch) -> None:
    """MIO_LOG_FORMAT=JSON (uppercase) should also trigger compact mode."""
    monkeypatch.setenv("MIO_LOG_FORMAT", "JSON")

    print_startup_banner("webcam", "127.0.0.1", 8000, version="1.0.0")

    captured = capsys.readouterr()
    assert "\n" not in captured.err.strip()


# ---------------------------------------------------------------------------
# print_startup_banner — version auto-read
# ---------------------------------------------------------------------------


def test_banner_auto_reads_version_when_not_provided(capsys, monkeypatch, tmp_path) -> None:
    """When version is omitted, banner reads it from the VERSION file."""
    version_file = tmp_path / "VERSION"
    version_file.write_text("3.2.1\n", encoding="utf-8")

    import pi_camera_in_docker.banner as banner_module

    original_candidates = banner_module._VERSION_FILE_CANDIDATES
    monkeypatch.setattr(banner_module, "_VERSION_FILE_CANDIDATES", [version_file])
    monkeypatch.setenv("MIO_LOG_FORMAT", "text")

    try:
        print_startup_banner("webcam", "127.0.0.1", 8000)
    finally:
        monkeypatch.setattr(banner_module, "_VERSION_FILE_CANDIDATES", original_candidates)

    captured = capsys.readouterr()
    assert "3.2.1" in captured.err
