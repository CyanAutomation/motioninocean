"""Tests for the portable container readiness smoke-test helper."""

import os
import subprocess
from pathlib import Path


def write_executable(path: Path, contents: str) -> None:
    """Create an executable test double on the temporary PATH."""
    path.write_text(contents)
    path.chmod(0o755)


def test_smoke_script_runs_mock_container_and_waits_for_readiness(tmp_path):
    """Start the requested architecture and clean it up after /ready succeeds."""
    binary_dir = tmp_path / "bin"
    binary_dir.mkdir()
    docker_log = tmp_path / "docker.log"

    write_executable(
        binary_dir / "docker",
        "#!/bin/sh\n"
        'printf "%s\\n" "$*" >> "$DOCKER_LOG"\n'
        'if [ "$1" = "run" ]; then echo "container-id"; fi\n',
    )
    write_executable(
        binary_dir / "curl",
        "#!/bin/sh\n"
        'while [ "$#" -gt 0 ]; do\n'
        '  if [ "$1" = "--output" ]; then\n'
        '    printf \'{"status":"ready"}\\n\' > "$2"\n'
        "    exit 0\n"
        "  fi\n"
        "  shift\n"
        "done\n"
        "exit 1\n",
    )

    environment = os.environ.copy()
    environment.update(
        {
            "PATH": f"{binary_dir}:/usr/bin:/bin",
            "DOCKER_LOG": str(docker_log),
            "IMAGE_REF": "motion-in-ocean:smoke",
            "PLATFORM": "linux/amd64",
            "SMOKE_PORT": "18000",
        }
    )
    script = Path(__file__).parents[1] / "scripts" / "smoke-container-readiness.sh"

    result = subprocess.run(
        ["bash", str(script)],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    docker_commands = docker_log.read_text().splitlines()
    run_command = next(command for command in docker_commands if command.startswith("run "))
    assert "--platform linux/amd64" in run_command
    assert "--publish 18000:8000" in run_command
    assert "--env MIO_MOCK_CAMERA=true" in run_command
    assert "--env MIO_BIND_HOST=0.0.0.0" in run_command
    assert any(command == "rm --force motion-in-ocean-smoke-amd64" for command in docker_commands)
