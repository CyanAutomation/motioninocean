"""Contract coverage for the documentation check's Python environment."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_docs_check_installs_dependencies_in_an_isolated_venv(tmp_path: Path) -> None:
    fake_python = tmp_path / "python"
    fake_python.write_text(
        "#!/bin/sh\n"
        'printf "%s %s\\n" "$0" "$*" >> "$DOCS_FAKE_LOG"\n'
        'if [ "$1" = "-m" ] && [ "$2" = "venv" ]; then\n'
        '  mkdir -p "$3/bin"\n'
        '  cp "$0" "$3/bin/python"\n'
        'elif [ "$1" = "-c" ]; then\n'
        '  [ -f "$DOCS_FAKE_READY" ]\n'
        'elif [ "$1" = "-m" ] && [ "$2" = "pip" ] && [ "$3" = "install" ]; then\n'
        '  touch "$DOCS_FAKE_READY"\n'
        "fi\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    docs_venv = tmp_path / "docs-venv"
    log_file = tmp_path / "python-commands.log"
    ready_file = tmp_path / "docs-dependencies-ready"

    result = subprocess.run(
        [
            "make",
            "-s",
            "-f",
            str(ROOT / "Makefile"),
            "docs-check",
            f"PYTHON={fake_python}",
            f"DOCS_VENV={docs_venv}",
        ],
        cwd=tmp_path,
        env={
            **os.environ,
            "DOCS_FAKE_LOG": str(log_file),
            "DOCS_FAKE_READY": str(ready_file),
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    commands = log_file.read_text(encoding="utf-8")
    assert f"-m venv {docs_venv}" in commands
    expected_pip_command = (
        f"{docs_venv}/bin/python -m pip install -r {ROOT}/requirements.txt "
        f"-r {ROOT}/requirements-docs.txt"
    )
    assert expected_pip_command in commands
    assert f"{docs_venv}/bin/python -m sphinx" in commands
    check_command = next(line for line in commands.splitlines() if " -c " in line)
    assert all(module in check_command for module in ("flask", "flask_compress", "PIL"))
    pip_commands = [line for line in commands.splitlines() if "-m pip install -r" in line]
    assert pip_commands == [expected_pip_command]


def test_default_docs_venv_is_anchored_to_makefile_directory(tmp_path: Path) -> None:
    result = subprocess.run(
        ["make", "-s", "-n", "-f", str(ROOT / "Makefile"), "ensure-docs-tools"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    expected_venv = ROOT / ".venv-docs"
    assert result.returncode == 0, result.stdout + result.stderr
    assert f'-m venv "{expected_venv}"' in result.stdout
    assert f'"{expected_venv}/bin/python"' in result.stdout
