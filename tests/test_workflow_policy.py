"""Regression checks for repository GitHub Actions security and policy."""

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
        "security-scan.yml": "scan",
    }

    for filename, job_name in checks.items():
        workflow = load_workflow(workspace_root, filename)
        condition = workflow["jobs"][job_name]["if"]
        assert (
            "github.ref == format('refs/heads/{0}', github.event.repository.default_branch)"
            in condition
        )


def test_kaseki_workflows_target_main_without_github_token_permissions(workspace_root):
    """Keep both Kaseki jobs on main and deny the unused workflow token."""
    jobs = {
        "kaseki-docs.yaml": {"system_status", "readiness", "api_connection", "dispatch"},
        "kaseki-dry.yaml": {"dry_sweep"},
    }

    for filename, job_names in jobs.items():
        workflow = load_workflow(workspace_root, filename)
        ref = workflow.get("env", {}).get("REF")
        if ref is None:
            ref = workflow["jobs"]["dry_sweep"]["env"]["REF"]

        assert workflow["permissions"] == {}
        assert ref == "main"
        assert "@main" in workflow["run-name"]
        assert set(workflow["jobs"]) == job_names
        assert all(
            workflow["jobs"][job_name]["if"] == "github.ref == 'refs/heads/main'"
            for job_name in job_names
        )


def test_kaseki_workflows_use_existing_validation_commands(workspace_root):
    """Use CI validation for code changes and Sphinx validation for docs changes."""
    docs = load_workflow(workspace_root, "kaseki-docs.yaml")
    docs_command = docs["env"]["VALIDATION_COMMAND"]
    makefile = (workspace_root / "Makefile").read_text()
    assert docs_command == "make docs-check"
    assert re.search(r"(?m)^docs-check\s*:", makefile)

    dry = load_workflow(workspace_root, "kaseki-dry.yaml")
    dry_command = dry["jobs"]["dry_sweep"]["env"]["VALIDATION_COMMAND"]
    assert dry_command == "make ci"
    assert re.search(r"(?m)^ci\s*:", makefile)


def test_kaseki_workflows_check_api_capabilities_and_preflight(workspace_root):
    """Reject unsupported modes and unavailable runner prerequisites before dispatch."""
    workflows = {
        "kaseki-docs.yaml": "dispatch",
        "kaseki-dry.yaml": "dry_sweep",
    }

    for filename, job_name in workflows.items():
        workflow = load_workflow(workspace_root, filename)
        steps = workflow["jobs"][job_name]["steps"]
        capabilities = next(
            step for step in steps if step.get("name") == "Verify Kaseki API capabilities"
        )
        preflight = next(
            step for step in steps if step.get("name") == "Verify Kaseki runner preflight"
        )

        # Kaseki mounts its public API under /api/v1; only health/readiness
        # probes remain at the root.
        assert "$KASEKI_BASE_URL/api/v1/capabilities" in capabilities["run"]
        assert 'index("patch")' in capabilities["run"]
        assert 'index("pr")' in capabilities["run"]
        assert capabilities["env"]["KASEKI_API_TOKEN"] == "${{ secrets.KASEKI_API_TOKEN }}"

        assert "$KASEKI_BASE_URL/api/v1/preflight" in preflight["run"]
        assert ".failedChecks" in preflight["run"]
        assert ".errors" in preflight["run"]
        assert preflight["env"]["KASEKI_API_TOKEN"] == "${{ secrets.KASEKI_API_TOKEN }}"
        assert steps.index(capabilities) < steps.index(preflight)
        submit = next(step for step in steps if step.get("id") == "submit")
        assert steps.index(preflight) < steps.index(submit)


def test_kaseki_workflows_use_supported_publish_mode_and_expose_noop_success(workspace_root):
    """Use the API's PR mode and make expected empty diffs successful outcomes."""
    workflows = {
        "kaseki-docs.yaml": ("dispatch", "Wait for Kaseki completion"),
        "kaseki-dry.yaml": ("dry_sweep", "Wait for Kaseki completion"),
    }

    for filename, (job_name, wait_name) in workflows.items():
        workflow = load_workflow(workspace_root, filename)
        job = workflow["jobs"][job_name]
        steps = job["steps"]
        submit = next(step for step in steps if step.get("id") == "submit")
        wait = next(step for step in steps if step.get("name") == wait_name)
        summary = next(step for step in steps if step.get("if") == "always()")

        assert 'publishMode: "pr"' in submit["run"]
        assert "failureClass" in wait["run"]
        assert '"empty-diff"' in wait["run"]
        assert "no_changes" in wait["run"]
        assert "FINAL_STATUS" in summary["run"]
        assert summary["run"].count('echo "| Mode |') == 1
        assert job["timeout-minutes"] == 200

    docs_steps = load_workflow(workspace_root, "kaseki-docs.yaml")["jobs"]["dispatch"]["steps"]
    docs_submit = next(step for step in docs_steps if step.get("id") == "submit")
    assert "goalSetting" not in docs_submit["run"]


def test_kaseki_submission_errors_report_structured_controller_details(workspace_root):
    """Expose the API's safe error and request ID fields, not the raw body."""
    workflows = {
        "kaseki-docs.yaml": "dispatch",
        "kaseki-dry.yaml": "dry_sweep",
    }

    for filename, job_name in workflows.items():
        workflow = load_workflow(workspace_root, filename)
        submit = next(
            step for step in workflow["jobs"][job_name]["steps"] if step.get("id") == "submit"
        )
        assert ".error" in submit["run"]
        assert ".requestId" in submit["run"]


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


def test_docker_release_scans_candidate_digest_before_promoting_tags(workspace_root):
    """Only a scanned and smoke-tested candidate may receive production image tags."""
    workflow = load_workflow(workspace_root, "docker-publish.yml")
    build = workflow["jobs"]["build"]
    scan = workflow["jobs"]["scan"]
    arm64 = workflow["jobs"]["arm64-smoke"]
    publish = workflow["jobs"]["publish"]

    assert build["outputs"]["image_ref"] == "${{ steps.candidate-ref.outputs.image_ref }}"
    build_push = next(step for step in build["steps"] if step.get("id") == "build_candidate")
    assert build_push["with"]["tags"] == "${{ steps.meta.outputs.tags }}"
    candidate_meta = next(
        step for step in build["steps"] if step.get("name") == "Extract candidate image metadata"
    )
    assert "type=raw,value=release-candidate" in candidate_meta["with"]["tags"]
    assert "cyanautomation/motioninocean" not in build_push["with"]["tags"]

    assert scan["needs"] == "build"
    scan_steps = scan["steps"]
    for platform in ("amd64", "arm64"):
        pull = next(
            step for step in scan_steps if step.get("name") == f"Pull {platform} candidate image"
        )
        scan_step = next(
            step
            for step in scan_steps
            if step.get("name") == f"Enforce HIGH and CRITICAL vulnerabilities on {platform}"
        )
        assert pull["env"]["IMAGE_REF"] == f"${{{{ needs.build.outputs.{platform}_ref }}}}"
        assert scan_step["with"]["image-ref"] == f"motion-in-ocean:scan-{platform}"
        assert scan_step["with"]["severity"] == "HIGH,CRITICAL"
        assert scan_step["with"]["exit-code"] == "1"

    assert arm64["needs"] == "build"
    smoke = next(step for step in arm64["steps"] if "docker run --rm" in step.get("run", ""))
    assert smoke["env"]["IMAGE_REF"] == "${{ needs.build.outputs.image_ref }}"
    assert publish["needs"] == ["build", "scan", "arm64-smoke"]
    assert publish["environment"]["name"] == "container-release"
    promote = next(
        step for step in publish["steps"] if step.get("name") == "Promote verified image tags"
    )
    assert "docker buildx imagetools create" in promote["run"]
    assert "${{ needs.build.outputs.image_ref }}" in promote["env"]["IMAGE_REF"]


def test_docker_release_uses_scoped_credentials_for_manual_release_events(workspace_root):
    """Protect publishing credentials and leave GitHub Release publication manual."""
    workflow = load_workflow(workspace_root, "docker-publish.yml")
    assert workflow["permissions"] == {}
    assert workflow["jobs"]["build"]["permissions"] == {
        "contents": "read",
        "packages": "write",
    }
    assert "release" not in workflow["jobs"]
    publish = workflow["jobs"]["publish"]
    assert "contents" not in publish["permissions"] or publish["permissions"]["contents"] == "read"
    assert publish["outputs"]["dockerhub_digest"] == (
        "${{ steps.published-images.outputs.dockerhub_digest }}"
    )
    hub_login = next(
        step for step in publish["steps"] if step.get("name") == "Log in to Docker Hub"
    )
    assert hub_login["with"]["username"] == "${{ secrets.RELEASE_DOCKERHUB_USERNAME }}"
    assert hub_login["with"]["password"] == "${{ secrets.RELEASE_DOCKERHUB_TOKEN }}"

    for job_name in ("verify", "build", "publish"):
        condition = workflow["jobs"][job_name]["if"]
        assert (
            "github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/main'"
            in condition
        )
        assert "github.event_name == 'release'" in condition


def test_release_settings_document_environment_approval_and_required_arm64_check(workspace_root):
    """Document the GitHub-side controls that YAML cannot configure itself."""
    guidance = (workspace_root / ".github" / "BRANCH_PROTECTION.md").read_text()

    assert "ARM64 Image Smoke Test" in guidance
    assert "container-release" in guidance
    assert "RELEASE_DOCKERHUB_USERNAME" in guidance
    assert "RELEASE_DOCKERHUB_TOKEN" in guidance
    assert "required reviewers" in guidance.lower()
    ruleset_example = guidance.split("## Ruleset Example", maxsplit=1)[1]
    status_checks = ruleset_example.split("3. **Block force pushes**", maxsplit=1)[0]
    assert "`ARM64 Image Smoke Test`" in status_checks


def test_docker_publish_does_not_create_or_edit_github_releases(workspace_root):
    """GitHub Releases are published and edited manually through the GitHub UI."""
    workflow = load_workflow(workspace_root, "docker-publish.yml")
    workflow_text = (workspace_root / ".github" / "workflows" / "docker-publish.yml").read_text()

    assert "release" not in workflow["jobs"]
    assert "gh release create" not in workflow_text
    assert "gh release edit" not in workflow_text


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


def test_ci_and_release_checkouts_do_not_persist_credentials(workspace_root):
    """Do not leave GitHub credentials available while repository code runs."""
    for filename in ("ci.yml", "docker-publish.yml"):
        workflow = load_workflow(workspace_root, filename)
        checkouts = [
            step
            for job in workflow["jobs"].values()
            for step in job.get("steps", [])
            if step.get("uses", "").startswith("actions/checkout@")
        ]

        assert checkouts
        assert all(step.get("with", {}).get("persist-credentials") is False for step in checkouts)


def test_ci_and_release_use_node_22(workspace_root):
    """Keep Node-based CI checks on the same maintained runtime as frontend tests."""
    for filename in ("ci.yml", "docker-publish.yml"):
        workflow = load_workflow(workspace_root, filename)
        node_steps = [
            step
            for job in workflow["jobs"].values()
            for step in job.get("steps", [])
            if step.get("uses", "").startswith("actions/setup-node@")
        ]

        assert node_steps
        assert all(str(step.get("with", {}).get("node-version")) == "22" for step in node_steps)


def test_ci_lints_action_workflows(workspace_root):
    """Run actionlint against every workflow in the CI lint job."""
    workflow = load_workflow(workspace_root, "ci.yml")
    steps = workflow["jobs"]["lint"]["steps"]

    setup_go = next(step for step in steps if step.get("uses", "").startswith("actions/setup-go@"))
    assert setup_go["with"]["go-version"] == "1.25.x"

    actionlint = next(step for step in steps if step.get("name") == "Lint GitHub Actions workflows")
    assert "go install github.com/rhysd/actionlint/cmd/actionlint@v1.7.12" in actionlint["run"]
    assert '-ignore \'unexpected key "queue" for "concurrency" section\'' in actionlint["run"]
    assert ".github/workflows/*.yml .github/workflows/*.yaml" in actionlint["run"]


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
        "Verify Kaseki API capabilities",
        "Verify Kaseki runner preflight",
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
    """Publish signed provenance for the verified image digests in both registries."""
    workflow = load_workflow(workspace_root, "docker-publish.yml")
    publish = workflow["jobs"]["publish"]
    assert publish["permissions"]["attestations"] == "write"
    assert publish["permissions"]["id-token"] == "write"
    assert publish["permissions"]["artifact-metadata"] == "write"

    attest_steps = [
        step for step in publish["steps"] if step.get("uses", "").startswith("actions/attest@")
    ]
    assert len(attest_steps) == 2
    verify_index = next(
        index
        for index, step in enumerate(publish["steps"])
        if step.get("name") == "Verify promoted multi-architecture manifests"
    )
    attest_indices = [publish["steps"].index(step) for step in attest_steps]
    assert verify_index < min(attest_indices)
    assert all(re.fullmatch(r"actions/attest@[0-9a-f]{40}", step["uses"]) for step in attest_steps)
    assert {step["with"]["subject-name"] for step in attest_steps} == {
        "ghcr.io/cyanautomation/motioninocean",
        "index.docker.io/cyanautomation/motioninocean",
    }
    assert {step["with"]["subject-digest"] for step in attest_steps} == {
        "${{ steps.published-images.outputs.ghcr_digest }}",
        "${{ steps.published-images.outputs.dockerhub_digest }}",
    }
    assert all(step["with"]["push-to-registry"] is True for step in attest_steps)
