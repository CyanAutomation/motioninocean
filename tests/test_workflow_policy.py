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
        "security-scan.yml": "scan",
    }

    for filename, job_name in checks.items():
        workflow = load_workflow(workspace_root, filename)
        condition = workflow["jobs"][job_name]["if"]
        assert (
            "github.ref == format('refs/heads/{0}', github.event.repository.default_branch)"
            in condition
        )


def test_kaseki_runs_only_on_main(workspace_root):
    """Scheduled and dispatched Kaseki runs must always target main."""
    workflow = load_workflow(workspace_root, "kaseki-dry.yaml")
    job = workflow["jobs"]["dry_sweep"]

    assert job["if"] == "github.ref == 'refs/heads/main'"
    assert job["env"]["REF"] == "main"
    assert "@main" in workflow["run-name"]


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


def test_docker_publish_serializes_mutable_tag_updates(workspace_root):
    """Schedule and release builds must not race while publishing stable tags."""
    workflow = load_workflow(workspace_root, "docker-publish.yml")
    concurrency = workflow["concurrency"]

    assert concurrency["group"] == "docker-release-publish"
    assert concurrency["queue"] == "max"


def test_security_enforcement_precedes_best_effort_reporting(workspace_root):
    """Reporting failures must not prevent the blocking Trivy scan from running."""
    workflow = load_workflow(workspace_root, "security-scan.yml")
    steps = workflow["jobs"]["scan"]["steps"]
    enforcement_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("name") == "Enforce HIGH and CRITICAL vulnerability policy"
    )
    report_names = {
        "Generate Trivy SARIF report",
        "Generate Trivy JSON report",
        "Generate Trivy human-readable report",
        "Upload Trivy reports",
    }
    report_indices = [index for index, step in enumerate(steps) if step.get("name") in report_names]

    assert report_indices
    assert enforcement_index < min(report_indices)
    for step in steps:
        if step.get("name") in {
            "Generate Trivy JSON report",
            "Generate Trivy human-readable report",
        }:
            assert step["if"] == "always() && steps.build_image.outcome == 'success'"
            assert step["continue-on-error"] is True
        if step.get("name") in report_names - {"Generate Trivy SARIF report"}:
            assert step["continue-on-error"] is True

    sarif_report = next(step for step in steps if step.get("name") == "Generate Trivy SARIF report")
    assert "continue-on-error" not in sarif_report


def test_autofix_requires_app_token_for_generated_prs(workspace_root):
    """Use an app token so checks for the generated PR trigger without approval."""
    workflow = load_workflow(workspace_root, "linting-autofix.yml")
    steps = workflow["jobs"]["autofix"]["steps"]
    token_check = next(step for step in steps if step.get("name") == "Require autofix app token")
    create_pr = next(step for step in steps if step.get("name") == "Create Pull Request")

    assert token_check["if"] == "steps.verify-changes.outputs.has-changes == 'true'"
    assert token_check["env"]["AUTOFIX_GITHUB_TOKEN"] == "${{ secrets.AUTOFIX_GITHUB_TOKEN }}"
    assert create_pr["with"]["token"] == "${{ secrets.AUTOFIX_GITHUB_TOKEN }}"


def test_kaseki_dry_scopes_token_and_pins_controller_host(workspace_root):
    """Only API steps receive the token, and only the approved controller is used."""
    workflow = load_workflow(workspace_root, "kaseki-dry.yaml")
    job = workflow["jobs"]["dry_sweep"]
    assert "KASEKI_API_TOKEN" not in job["env"]

    validation = next(
        step for step in job["steps"] if step.get("name") == "Validate Kaseki configuration"
    )
    assert '"https://kaseki-tunnel.scheimann.xyz"' in validation["run"]

    token_steps = {
        "Verify gateway connectivity and authentication",
        "Submit DRY sweep",
        "Wait for Kaseki completion",
    }
    found_token_steps = set()
    for step in job["steps"]:
        if step.get("name") in token_steps:
            found_token_steps.add(step["name"])
            assert step["env"]["KASEKI_API_TOKEN"] == "${{ secrets.KASEKI_API_TOKEN }}"
    assert found_token_steps == token_steps


def test_docker_publish_attests_both_registry_images(workspace_root):
    """Publish signed provenance for the shared image digest in both registries."""
    workflow = load_workflow(workspace_root, "docker-publish.yml")
    build = workflow["jobs"]["build"]
    assert build["permissions"]["attestations"] == "write"
    assert build["permissions"]["id-token"] == "write"
    assert build["permissions"]["artifact-metadata"] == "write"

    attest_steps = [
        step for step in build["steps"] if step.get("uses", "").startswith("actions/attest@")
    ]
    assert len(attest_steps) == 2
    verify_index = next(
        index
        for index, step in enumerate(build["steps"])
        if step.get("name") == "Verify published multi-architecture manifest"
    )
    attest_indices = [build["steps"].index(step) for step in attest_steps]
    assert verify_index < min(attest_indices)
    assert all(re.fullmatch(r"actions/attest@[0-9a-f]{40}", step["uses"]) for step in attest_steps)
    assert {step["with"]["subject-name"] for step in attest_steps} == {
        "ghcr.io/cyanautomation/motioninocean",
        "index.docker.io/cyanautomation/motioninocean",
    }
    assert all(
        step["with"]["subject-digest"] == "${{ steps.build_bookworm.outputs.digest }}"
        and step["with"]["push-to-registry"] is True
        for step in attest_steps
    )
