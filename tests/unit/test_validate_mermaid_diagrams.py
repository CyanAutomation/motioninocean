import json
import subprocess
from pathlib import Path

import pytest

from scripts import validate_mermaid_diagrams


def test_extract_mermaid_diagrams_ignores_other_code_fences_and_supports_fence_styles():
    markdown = """# Guide

```python
not a diagram
```

```mermaid
flowchart TD
  A --> B
```

~~~{mermaid}
sequenceDiagram
  A->>B: hello
~~~
"""

    assert validate_mermaid_diagrams.extract_mermaid_diagrams(markdown) == [
        "flowchart TD\n  A --> B\n",
        "sequenceDiagram\n  A->>B: hello\n",
    ]


def test_extract_mermaid_diagrams_rejects_an_unclosed_fence():
    with pytest.raises(validate_mermaid_diagrams.MermaidFenceError):
        validate_mermaid_diagrams.extract_mermaid_diagrams("```mermaid\nflowchart TD\n")


def test_validate_files_sends_only_diagram_sources_to_the_renderer(
    monkeypatch, tmp_path: Path, capsys
):
    source = tmp_path / "guide.md"
    source.write_text(
        "# Guide\n\n```mermaid\ngraph TD\n A-->B\n```\n\n"
        "~~~{mermaid}\nstateDiagram-v2\n [*] --> Ready\n~~~\n",
        encoding="utf-8",
    )
    rendered_sources: list[str] = []

    def render(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert kwargs["check"] is False
        input_index = args.index("-i") + 1
        rendered_sources.append(Path(args[input_index]).read_text(encoding="utf-8"))
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(validate_mermaid_diagrams.subprocess, "run", render)

    result = validate_mermaid_diagrams.validate_files([source], "mmdc")

    assert result == 0
    assert rendered_sources == ["graph TD\n A-->B\n", "stateDiagram-v2\n [*] --> Ready\n"]
    assert "Validated 2 Mermaid diagram(s)" in capsys.readouterr().out


def test_validate_files_disables_browser_sandbox_for_renderer(monkeypatch, tmp_path: Path):
    source = tmp_path / "guide.md"
    source.write_text("```mermaid\nflowchart TD\n A-->B\n```\n", encoding="utf-8")
    monkeypatch.delenv("PUPPETEER_EXECUTABLE_PATH", raising=False)
    monkeypatch.setattr(validate_mermaid_diagrams.shutil, "which", lambda _name: None)
    observed_config: dict[str, object] = {}

    def render(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        config_index = args.index("--puppeteerConfigFile") + 1
        observed_config.update(json.loads(Path(args[config_index]).read_text(encoding="utf-8")))
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(validate_mermaid_diagrams.subprocess, "run", render)

    assert validate_mermaid_diagrams.validate_files([source], "mmdc") == 0
    assert observed_config["args"] == ["--no-sandbox", "--disable-setuid-sandbox"]


def test_validate_files_returns_renderer_failure_with_document_context(
    monkeypatch, tmp_path: Path, capsys
):
    source = tmp_path / "guide.md"
    source.write_text("```mermaid\nflowchart TD\n A-->B\n```\n", encoding="utf-8")
    calls = 0

    def fail_render(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        nonlocal calls
        calls += 1
        return subprocess.CompletedProcess(args, 19, stdout="renderer output", stderr="bad syntax")

    monkeypatch.setattr(validate_mermaid_diagrams.subprocess, "run", fail_render)

    result = validate_mermaid_diagrams.validate_files([source], "mmdc")

    assert result == 19
    assert calls == 1
    captured = capsys.readouterr()
    assert str(source) in captured.err
    assert "renderer output" in captured.err
    assert "bad syntax" in captured.err


def test_validate_files_rejects_a_document_without_diagrams_before_rendering(
    monkeypatch, tmp_path: Path, capsys
):
    source = tmp_path / "guide.md"
    source.write_text("# No diagrams here\n", encoding="utf-8")
    monkeypatch.setattr(
        validate_mermaid_diagrams.subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail("renderer should not be called"),
    )

    assert validate_mermaid_diagrams.validate_files([source], "mmdc") == 1
    assert "no Mermaid diagrams found" in capsys.readouterr().err
