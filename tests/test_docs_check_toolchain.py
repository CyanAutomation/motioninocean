"""Contract coverage for the documentation check's Python environment."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DocsCheckToolchainTests(unittest.TestCase):
    def test_docs_check_installs_dependencies_in_an_isolated_venv(self) -> None:
        with tempfile.TemporaryDirectory(prefix="docs-check-toolchain-") as temporary:
            temp_path = Path(temporary)
            fake_python = temp_path / "python"
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
                'fi\n',
                encoding="utf-8",
            )
            fake_python.chmod(0o755)
            docs_venv = temp_path / "docs-venv"
            log_file = temp_path / "python-commands.log"
            ready_file = temp_path / "docs-dependencies-ready"

            result = subprocess.run(
                [
                    "make", "-s", "docs-check",
                    f"PYTHON={fake_python}",
                    f"DOCS_VENV={docs_venv}",
                ],
                cwd=ROOT,
                env={
                    **os.environ,
                    "DOCS_FAKE_LOG": str(log_file),
                    "DOCS_FAKE_READY": str(ready_file),
                },
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            commands = log_file.read_text(encoding="utf-8")
            self.assertIn(f"-m venv {docs_venv}", commands)
            self.assertIn(f"{docs_venv}/bin/python -m pip install -r requirements-docs.txt", commands)
            self.assertIn(f"{docs_venv}/bin/python -m sphinx", commands)
            pip_commands = [line for line in commands.splitlines() if "-m pip install -r" in line]
            self.assertEqual(pip_commands, [f"{docs_venv}/bin/python -m pip install -r requirements-docs.txt"])


if __name__ == "__main__":
    unittest.main()
