"""Focused tests for shell-free provenance commands in logging configuration."""

import logging
from unittest import mock

import pytest

from pi_camera_in_docker import logging_config


@pytest.mark.parametrize(
    ("available_command", "expected_command"),
    [
        ("rpicam-hello", "rpicam-hello"),
        ("libcamera-hello", "libcamera-hello"),
        ("unexpected-camera-cli", None),
    ],
    ids=("preferred", "fallback", "unlisted"),
)
def test_detect_cli_only_selects_allowlisted_commands(
    monkeypatch: pytest.MonkeyPatch,
    available_command: str,
    expected_command: str | None,
) -> None:
    """Camera CLI detection selects only the fixed candidate allowlist."""
    which = mock.Mock(side_effect=lambda command: command if command == available_command else None)
    monkeypatch.setattr(logging_config.shutil, "which", which)

    assert logging_config._detect_camera_cli() == expected_command
    assert [call.args[0] for call in which.call_args_list] == list(
        logging_config.CAMERA_CLI_CANDIDATES[: len(which.call_args_list)]
    )


def test_capture_cli_version_uses_separate_version_argument(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Camera version capture passes the literal flag separately without a shell."""
    monkeypatch.setattr(logging_config.shutil, "which", lambda command: f"/usr/bin/{command}")
    run = mock.Mock(return_value=mock.Mock(returncode=0, stdout="rpicam-apps v1.2.3\n", stderr=""))
    monkeypatch.setattr(logging_config.subprocess, "run", run)

    version, command = logging_config._capture_camera_cli_version(logging.getLogger(__name__))

    assert (version, command) == ("rpicam-apps v1.2.3", "rpicam-hello")
    run.assert_called_once_with(
        ["rpicam-hello", "--version"],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )


def test_package_provenance_is_reported_from_a_shell_free_query(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Camera package origin information reaches startup logs using a fixed argv."""
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(
        logging_config, "_capture_camera_cli_version", lambda logger: ("unknown", "none")
    )
    monkeypatch.setattr(logging_config.Path, "exists", lambda path: False)
    monkeypatch.setattr(logging_config, "is_flag_enabled", lambda flag: False)
    run = mock.Mock(
        return_value=mock.Mock(
            returncode=0,
            stdout="libcamera-apps\t1.2.3\tRaspberry Pi\n",
            stderr="",
        )
    )
    monkeypatch.setattr(logging_config.subprocess, "run", run)

    logging_config.log_provenance_info()

    assert "package_origins=Raspberry Pi" in caplog.text
    command = run.call_args.args[0]
    assert command == [
        logging_config.DPKG_QUERY_PATH,
        "-W",
        "-f=${Package}\t${Version}\t${Origin}\n",
        "libcamera-apps",
        "python3-picamera2",
        "python3-libcamera",
    ]
    assert run.call_args.kwargs == {
        "capture_output": True,
        "text": True,
        "timeout": 5,
        "check": False,
    }
