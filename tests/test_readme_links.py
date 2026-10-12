"""Keep local links in the root README pointed at existing files."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


REPO_ROOT = Path(__file__).resolve().parents[1]
README_PATH = REPO_ROOT / "README.md"


def test_root_readme_relative_links_resolve() -> None:
    markdown = README_PATH.read_text(encoding="utf-8")
    # Match each destination independently so linked badges such as
    # `[![License](badge.svg)](LICENSE)` have both targets checked.
    links = re.findall(r"\]\(([^)]+)\)", markdown)
    broken_links: list[str] = []

    for raw_target in links:
        target = raw_target.split(maxsplit=1)[0].strip("<>")
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue

        destination = (README_PATH.parent / unquote(parsed.path)).resolve()
        if not destination.exists():
            broken_links.append(parsed.path)

    assert not broken_links, "Broken root README links:\n" + "\n".join(broken_links)
