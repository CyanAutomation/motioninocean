"""Keep repository skills accurate, complete, and navigable."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / ".github" / "skills"
REQUIRED_HEADINGS = (
    "Purpose",
    "Scope and trigger conditions",
    "Required inputs",
    "Step-by-step workflow",
    "Validation checklist",
    "Source of truth",
    "Common failure modes and recovery actions",
    "Related Skills",
    "Maintenance notes",
)


def _skill_markdown_files() -> list[Path]:
    return sorted(SKILLS_ROOT.glob("*/SKILL.md"))


def _make_targets() -> set[str]:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    return {match.group(1) for match in re.finditer(r"^([A-Za-z0-9_.-]+):", makefile, re.MULTILINE)}


def _markdown_links(markdown: str) -> list[str]:
    return re.findall(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", markdown)


def test_every_skill_has_required_metadata_and_sections() -> None:
    required_metadata = {
        "name",
        "description",
        "owner",
        "last-reviewed",
        "category",
        "compatible-repo-areas",
    }
    for path in _skill_markdown_files():
        content = path.read_text(encoding="utf-8")
        assert content.startswith("---\n"), f"{path.relative_to(REPO_ROOT)} has no frontmatter"
        frontmatter = content.split("---\n", 2)[1]
        metadata = {
            line.split(":", 1)[0].strip()
            for line in frontmatter.splitlines()
            if ":" in line and not line.lstrip().startswith("-")
        }
        assert required_metadata <= metadata, (
            f"{path.relative_to(REPO_ROOT)} is missing metadata: "
            f"{sorted(required_metadata - metadata)}"
        )
        review_date = re.search(r"^last-reviewed:\s*(\S+)\s*$", frontmatter, re.MULTILINE)
        valid_review_date = review_date and (
            review_date.group(1) == "YYYY-MM-DD"
            if path.parent.name == "_template"
            else re.fullmatch(r"\d{4}-\d{2}-\d{2}", review_date.group(1))
        )
        assert valid_review_date, f"{path.relative_to(REPO_ROOT)} needs an ISO last-reviewed date"
        for heading in REQUIRED_HEADINGS:
            assert f"## {heading}" in content, (
                f"{path.relative_to(REPO_ROOT)} is missing section {heading!r}"
            )


def test_skill_markdown_links_resolve_inside_repository() -> None:
    broken_links: list[str] = []
    for markdown_path in sorted(SKILLS_ROOT.rglob("*.md")):
        content = markdown_path.read_text(encoding="utf-8")
        for raw_target in _markdown_links(content):
            target = raw_target.split(maxsplit=1)[0].strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            destination = (markdown_path.parent / unquote(parsed.path)).resolve()
            if not destination.exists():
                broken_links.append(f"{markdown_path.relative_to(REPO_ROOT)} -> {parsed.path}")
    assert not broken_links, "Broken skill links:\n" + "\n".join(broken_links)


def test_skill_references_use_defined_make_and_npm_commands() -> None:
    make_targets = _make_targets()
    package = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
    npm_scripts = set(package["scripts"])
    missing: list[str] = []

    for path in sorted(SKILLS_ROOT.rglob("*.md")):
        content = path.read_text(encoding="utf-8")
        code_samples = re.findall(r"```[^\n]*\n(.*?)```", content, re.DOTALL)
        code_samples.extend(re.findall(r"`([^`\n]+)`", content))
        for sample in code_samples:
            for line in sample.splitlines():
                command = line.strip().removeprefix("$").strip()
                if command.startswith("#"):
                    continue
                for match in re.finditer(r"\bmake\s+([a-z][a-z0-9-]*)\b", command):
                    if match.group(1) not in make_targets:
                        missing.append(f"{path.relative_to(REPO_ROOT)}: make {match.group(1)}")
                for match in re.finditer(r"\bnpm\s+run\s+([a-z][a-z0-9:_-]*)\b", command):
                    if match.group(1) not in npm_scripts:
                        missing.append(f"{path.relative_to(REPO_ROOT)}: npm run {match.group(1)}")

    assert not missing, "Skill docs reference undefined commands:\n" + "\n".join(missing)


def test_diagram_validation_inputs_exist_and_failures_propagate(tmp_path: Path) -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    recipe = makefile.split("validate-diagrams:\n", 1)[1].split("\n\n", 1)[0]
    script_call = re.search(r"scripts/validate_mermaid_diagrams\.py\s+([^\n]+)", recipe)
    assert script_call, "The diagram target must use the Markdown diagram extractor"
    inputs = script_call.group(1).split()
    assert inputs, "The diagram validation target must render at least one file"
    assert all((REPO_ROOT / source).is_file() for source in inputs), (
        f"Diagram validation references missing files: "
        f"{[source for source in inputs if not (REPO_ROOT / source).is_file()]}"
    )

    renderer = tmp_path / "mmdc"
    log_path = tmp_path / "rendered-diagrams.txt"
    renderer.write_text(
        "#!/bin/sh\n"
        'while [ "$#" -gt 0 ]; do\n'
        '  if [ "$1" = "-i" ]; then cat "$2" >> "$MMD_LOG"; '
        'printf "\\n---\\n" >> "$MMD_LOG"; shift 2; else shift; fi\n'
        "done\n",
        encoding="utf-8",
    )
    renderer.chmod(0o755)
    test_env = os.environ.copy()
    test_env["PATH"] = f"{tmp_path}:{os.environ['PATH']}"
    test_env["MMD_LOG"] = str(log_path)
    success = subprocess.run(
        ["make", "validate-diagrams"],
        cwd=REPO_ROOT,
        env=test_env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert success.returncode == 0, success.stdout + success.stderr
    rendered = [
        block for block in log_path.read_text(encoding="utf-8").split("\n---\n") if block.strip()
    ]
    assert len(rendered) >= 12, "Each Mermaid code block must be rendered separately"
    assert all(
        block.strip().startswith(("flowchart", "graph", "sequenceDiagram", "stateDiagram"))
        for block in rendered
    ), "The renderer must receive Mermaid source, not the surrounding Markdown"

    renderer.write_text("#!/bin/sh\nexit 19\n", encoding="utf-8")
    failure = subprocess.run(
        ["make", "validate-diagrams"],
        cwd=REPO_ROOT,
        env={"PATH": f"{tmp_path}:{os.environ['PATH']}"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert failure.returncode != 0, "Renderer errors must fail diagram validation"


def test_run_mock_uses_the_canonical_flag_environment() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    recipe = makefile.split("run-mock:\n", 1)[1].split("\n\n", 1)[0]
    assert "MIO_MOCK_CAMERA=true" in recipe


def test_feature_flag_check_uses_selected_python_interpreter() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    recipe = makefile.split("check-feature-flag-usage:\n", 1)[1].split("\n\n", 1)[0]
    assert "$(PYTHON) -m pi_camera_in_docker.feature_flag_usage_check" in recipe


def test_docs_check_uses_selected_python_and_propagates_build_failure(tmp_path: Path) -> None:
    fake_python = tmp_path / "python"
    fake_python.write_text(
        "#!/bin/sh\n"
        'case "$*" in\n'
        '  *"-c "*) exit 0 ;;\n'
        '  *"-m sphinx "*) echo "simulated Sphinx failure" >&2; exit 19 ;;\n'
        "  *) exit 20 ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    result = subprocess.run(
        ["make", "docs-check", f"PYTHON={fake_python}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0, "Sphinx failures must fail the docs check"
    assert "simulated Sphinx failure" in result.stdout + result.stderr
