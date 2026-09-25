#!/usr/bin/env python3
"""Validate Mermaid fences embedded in Markdown documents with mermaid-cli."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


MERMAID_FENCE = re.compile(r"^(?P<fence>`{3,}|~{3,})\s*\{?mermaid\}?\s*$", re.IGNORECASE)


class MermaidFenceError(ValueError):
    """Raised when a Mermaid code fence is not closed in Markdown."""


def extract_mermaid_diagrams(markdown: str) -> list[str]:
    """Return diagram source blocks from Mermaid and MyST Mermaid fences."""
    lines = markdown.splitlines()
    diagrams: list[str] = []
    index = 0

    while index < len(lines):
        opening = MERMAID_FENCE.fullmatch(lines[index].strip())
        if opening is None:
            index += 1
            continue

        fence = opening.group("fence")
        fence_char = fence[0]
        content: list[str] = []
        index += 1
        while index < len(lines):
            candidate = lines[index].strip()
            if re.fullmatch(rf"{re.escape(fence_char)}{{{len(fence)},}}", candidate):
                break
            content.append(lines[index])
            index += 1

        if index == len(lines):
            raise MermaidFenceError
        diagrams.append("\n".join(content).strip() + "\n")
        index += 1

    return diagrams


def validate_files(sources: list[Path], renderer: str) -> int:
    """Extract and validate each Mermaid diagram from the selected documents."""
    total = 0
    with tempfile.TemporaryDirectory(prefix="motioninocean-mermaid-") as temp_dir:
        temp_path = Path(temp_dir)
        for source_index, source in enumerate(sources):
            if not source.is_file():
                sys.stderr.write(f"Error: Mermaid source file does not exist: {source}\n")
                return 1

            try:
                diagrams = extract_mermaid_diagrams(source.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, ValueError) as exc:
                sys.stderr.write(f"Error reading Mermaid source {source}: {exc}\n")
                return 1

            if not diagrams:
                sys.stderr.write(f"Error: no Mermaid diagrams found in {source}\n")
                return 1

            for diagram_index, diagram in enumerate(diagrams):
                input_path = temp_path / f"source-{source_index}-diagram-{diagram_index}.mmd"
                output_path = temp_path / f"source-{source_index}-diagram-{diagram_index}.svg"
                input_path.write_text(diagram, encoding="utf-8")
                result = subprocess.run(
                    [
                        renderer,
                        "-i",
                        str(input_path),
                        "-o",
                        str(output_path),
                        "-t",
                        "dark",
                        "--quiet",
                    ],
                    capture_output=True,
                    check=False,
                    text=True,
                )
                if result.returncode:
                    sys.stderr.write(
                        f"Mermaid validation failed for {source} diagram {diagram_index + 1}:\n"
                    )
                    if result.stdout:
                        sys.stderr.write(result.stdout)
                    if result.stderr:
                        sys.stderr.write(result.stderr)
                    return result.returncode
                total += 1

            sys.stdout.write(f"Validated {len(diagrams)} Mermaid diagram(s) in {source}.\n")

    sys.stdout.write(f"Validated {total} Mermaid diagram(s) across {len(sources)} file(s).\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run Mermaid validation for the source documents passed on the command line."""
    arguments = argv if argv is not None else sys.argv[1:]
    if not arguments:
        sys.stderr.write("Usage: validate_mermaid_diagrams.py MARKDOWN_FILE [MARKDOWN_FILE ...]\n")
        return 2

    renderer = shutil.which("mmdc")
    if renderer is None:
        sys.stderr.write("Error: mermaid-cli is not installed or not on PATH.\n")
        return 1

    return validate_files([Path(argument) for argument in arguments], renderer)


if __name__ == "__main__":
    raise SystemExit(main())
