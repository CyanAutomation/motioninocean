"""Regression checks for repository GitHub Actions security and policy."""

import json
import re

import yaml


def load_workflow(workspace_root, filename):
    """Load a workflow by filename."""
    return yaml.safe_load((workspace_root / ".github" / "workflows" / filename).read_text())


def test_untrusted_security_scan_has_no_write_token(workspace_root):
    """Keep PR-controlled image builds away from SARIF write credentials."""
    workflow = load_workflow(workspace_root, "security-scan.yml")
    scan = workflow["jobs"]["scan"]
    checkout = next(
        step for step in scan["steps"] if step.get("uses", "").startswith("actions/checkout@")
    )

    assert scan["permissions"] == {"contents": "read"}
    assert scan["if"] == (
        "github.event_name != 'workflow_dispatch' || "
        "github.ref == format('refs/heads/{0}', github.event.repository.default_branch)"
    )
    assert checkout["with"]["persist-credentials"] is False

    arm64_smoke = workflow["jobs"]["arm64-smoke"]
    arm64_checkout = next(
        step
        for step in arm64_smoke["steps"]
        if step.get("uses", "").startswith("actions/checkout@")
    )
    assert arm64_checkout["with"]["persist-credentials"] is False

    upload = workflow["jobs"]["upload-sarif"]
    assert upload["needs"] == "scan"
    assert upload["permissions"] == {"security-events": "write"}
    assert "github.event_name == 'push'" in upload["if"]
    assert "github.event_name == 'workflow_dispatch'" in upload["if"]
    assert "github.event.repository.default_branch" in upload["if"]
    assert "needs.scan.outputs.sarif-produced == 'true'" in upload["if"]
    assert any(
        step.get("uses", "").startswith("actions/download-artifact@") for step in upload["steps"]
    )
    assert any(
        step.get("uses", "").startswith("github/codeql-action/upload-sarif@")
        for step in upload["steps"]
    )


def test_privileged_manual_workflows_are_default_branch_only(workspace_root):
    """Do not allow dispatching privileged jobs from a branch's workflow file."""
    checks = {
        "linting-autofix.yml": "autofix",
        "kaseki-dry.yaml": "dry_sweep",
        "security-scan.yml": "scan",
    }

    for filename, job_name in checks.items():
        workflow = load_workflow(workspace_root, filename)
        condition = workflow["jobs"][job_name]["if"]
        assert (
            "github.ref == format('refs/heads/{0}', github.event.repository.default_branch)"
            in condition
        )


def test_kaseki_workflows_use_existing_validation_commands(workspace_root):
    """Every command sent to Kaseki should exist in the repository."""
    package = json.loads((workspace_root / "package.json").read_text())
    scripts = package["scripts"]

    docs = load_workflow(workspace_root, "kaseki-docs.yaml")
    docs_command = docs["env"]["VALIDATION_COMMAND"]
    for command in docs_command.split(" && "):
        assert command.startswith("npm run ")
        assert command.removeprefix("npm run ") in scripts

    dry = load_workflow(workspace_root, "kaseki-dry.yaml")
    dry_command = dry["jobs"]["dry_sweep"]["env"]["VALIDATION_COMMAND"]
    assert dry_command == "make ci"
    assert re.search(r"(?m)^ci\s*:", (workspace_root / "Makefile").read_text())


def test_kaseki_dry_allowlist_covers_application_and_tests(workspace_root):
    """Allow the DRY sweep to refactor the actual app and frontend source paths."""
    workflow = load_workflow(workspace_root, "kaseki-dry.yaml")
    allowlist = set(workflow["jobs"]["dry_sweep"]["env"]["ALLOWLIST"].split(","))

    assert {
        "pi_camera_in_docker/**/*",
        "frontend/src/**/*",
        "scripts/**/*",
        "tests/**/*",
    } <= allowlist
    assert "src/**/*" not in allowlist
    assert "test/**/*" not in allowlist


def test_trivy_reports_include_unfixed_findings_but_gate_does_not(workspace_root):
    """Keep unfixed vulnerabilities visible without changing the blocking policy."""
    workflow = load_workflow(workspace_root, "security-scan.yml")
    steps = workflow["jobs"]["scan"]["steps"]

    for name in (
        "Generate Trivy SARIF report",
        "Generate Trivy JSON report",
        "Generate Trivy human-readable report",
    ):
        report = next(step for step in steps if step.get("name") == name)
        assert report["with"]["ignore-unfixed"] is False

    enforcement = next(
        step
        for step in steps
        if step.get("name") == "Enforce HIGH and CRITICAL vulnerability policy"
    )
    assert enforcement["with"]["ignore-unfixed"] is True
