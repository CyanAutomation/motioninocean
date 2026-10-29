#!/usr/bin/env python3
"""Write the content-derived static asset version used by the Docker image."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def derive_asset_version(static_directory: Path) -> str:
    """Hash static file paths and contents into the deployed asset version."""
    digest = hashlib.sha256()
    for path in sorted(item for item in static_directory.rglob("*") if item.is_file()):
        digest.update(path.relative_to(static_directory).as_posix().encode("utf-8"))
        digest.update(b"\0")
        with path.open("rb") as asset:
            for chunk in iter(lambda: asset.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()[:16]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("static_dir", type=Path)
    parser.add_argument("output_file", type=Path)
    args = parser.parse_args()
    args.output_file.write_text(derive_asset_version(args.static_dir) + "\n", encoding="ascii")
