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

    smoke_job = workflow["jobs"]["container-smoke"]
    smoke_checkout = next(
        step for step in smoke_job["steps"] if step.get("uses", "").startswith("actions/checkout@")
    )
    assert smoke_checkout["with"]["persist-credentials"] is False

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


def test_soyuz_workflows_target_main_with_read_only_checkout_permissions(workspace_root):
    """Keep both Soyuz submission jobs on main with minimum checkout access."""
    jobs = {
        "kaseki-docs.yaml": {"docs_sweep"},
        "kaseki-dry.yaml": {"dry_sweep"},
    }

    for filename, job_names in jobs.items():
        workflow = load_workflow(workspace_root, filename)
        job_name = next(iter(job_names))
        job = workflow["jobs"][job_name]

        assert workflow["permissions"] == {"contents": "read"}
        assert job["env"]["REF"] == "main"
        assert "${{ github.sha }}" in workflow["run-name"]
        assert set(workflow["jobs"]) == job_names
        assert job["if"] == "github.ref == 'refs/heads/main'"
        assert job["environment"] == "soyuz"
        assert job["timeout-minutes"] == 15

        checkout = next(step for step in job["steps"] if step.get("uses", "").startswith("actions/checkout@"))
        setup_node = next(step for step in job["steps"] if step.get("uses", "").startswith("actions/setup-node@"))
        assert checkout["with"] == {"ref": "${{ github.sha }}", "persist-credentials": False}
        assert setup_node["with"]["node-version"] == "26"

        workflow_text = (workspace_root / ".github" / "workflows" / filename).read_text()
        assert "KASEKI_" not in workflow_text
        assert "kaseki-agent" not in workflow_text
        assert "Verify Kaseki" not in workflow_text
        assert "Wait for Kaseki completion" not in workflow_text


def test_soyuz_workflows_use_existing_validation_commands(workspace_root):
    """Use CI validation for code changes and Sphinx validation for docs changes."""
    docs = load_workflow(workspace_root, "kaseki-docs.yaml")
    docs_command = docs["jobs"]["docs_sweep"]["env"]["VALIDATION_COMMAND"]
    makefile = (workspace_root / "Makefile").read_text()
    assert docs_command == "make docs-check"
    assert re.search(r"(?m)^docs-check\s*:", makefile)

    dry = load_workflow(workspace_root, "kaseki-dry.yaml")
    dry_command = dry["jobs"]["dry_sweep"]["env"]["VALIDATION_COMMAND"]
    assert dry_command == "make ci"
    assert re.search(r"(?m)^ci\s*:", makefile)


def test_soyuz_workflows_validate_configuration_and_submit_securely(workspace_root):
    """Validate the configured Soyuz origin and submit an authenticated idempotent request."""
    workflows = {
        "kaseki-docs.yaml": "docs_sweep",
        "kaseki-dry.yaml": "dry_sweep",
    }

    for filename, job_name in workflows.items():
        workflow = load_workflow(workspace_root, filename)
        steps = workflow["jobs"][job_name]["steps"]
        validate_url = next(step for step in steps if step.get("name") == "Validate Soyuz URL")
        submit = next(step for step in steps if step.get("id") == "submit")
        summary = next(step for step in steps if step.get("if") == "always()")

        assert validate_url["run"] == "node --experimental-strip-types scripts/validate-soyuz-url.ts"
        assert submit["env"]["SOYUZ_SUBMISSION_API_TOKEN"] == "${{ secrets.SOYUZ_SUBMISSION_API_TOKEN }}"
        assert '"$SOYUZ_BASE_URL/v1/runs"' in submit["run"]
        assert '"Authorization: Bearer $SOYUZ_SUBMISSION_API_TOKEN"' in submit["run"]
        assert '"Idempotency-Key: $idempotency_key"' in submit["run"]
        assert "--proto '=https' --tlsv1.2" in submit["run"]
        assert "^(200|202)$" in submit["run"]
        assert '"^soyuz-[0-9]+$"' in submit["run"]
        assert "validate-soyuz-run-id.ts" in submit["run"]
        assert "Response body omitted" in submit["run"]
        assert "Soyuz accepted" in submit["run"]
        assert any(
            label in summary["run"]
            for label in (
                "Soyuz documentation submission",
                "Soyuz DRY submission",
            )
        )
        assert "Accepted means Soyuz admitted the task" in summary["run"]


def test_soyuz_workflows_keep_repository_specific_commands_and_paths(workspace_root):
    """Keep the repo's own documentation and DRY validation settings during migration."""
    docs = load_workflow(workspace_root, "kaseki-docs.yaml")
    docs_env = docs["jobs"]["docs_sweep"]["env"]
    assert docs_env["ALLOWLIST"] == "README.md,docs/**/*.md"
    assert docs_env["VALIDATION_COMMAND"] == "make docs-check"
    assert docs_env["TASK_DESCRIPTION"] == (
        "Keep README.md and docs/ accurate against the current implementation."
    )
    assert docs[True]["schedule"][0]["cron"] == "0 5 * * 0"

    dry = load_workflow(workspace_root, "kaseki-dry.yaml")
    dry_env = dry["jobs"]["dry_sweep"]["env"]
    assert dry_env["ALLOWLIST"] == "pi_camera_in_docker/**/*,frontend/src/**/*,scripts/**/*,tests/**/*"
    assert dry_env["VALIDATION_COMMAND"] == "make ci"
    assert dry[True]["schedule"][0]["cron"] == "0 6 * * 1"

    for workflow, job_name in ((docs, "docs_sweep"), (dry, "dry_sweep")):
        job = workflow["jobs"][job_name]
        assert job["env"]["SOYUZ_BASE_URL"] == "${{ vars.SOYUZ_BASE_URL }}"
        assert "SOYUZ_BASE_URL" not in workflow.get("env", {})
        submit = next(step for step in job["steps"] if step.get("id") == "submit")
        assert 'taskMode: "patch"' in submit["run"]
        assert 'publishMode: "pr"' in submit["run"]
        assert "timeoutSeconds: 10800" in submit["run"]
        assert "maxDiffBytes: 102400" in submit["run"]
        assert "changedFilesAllowlist" in submit["run"]
        assert "validationCommands: [$validationCommand]" in submit["run"]

    docs_submit = next(
        step for step in docs["jobs"]["docs_sweep"]["steps"] if step.get("id") == "submit"
    )
    assert "scouting: { enabled: false }" in docs_submit["run"]
    assert "goalSetting: { enabled: false }" in docs_submit["run"]
    assert "goalCheck: { enabled: true, maxRetries: 1 }" in docs_submit["run"]
    assert "documentation-only changes" in docs_submit["run"]

    dry_submit = next(
        step for step in dry["jobs"]["dry_sweep"]["steps"] if step.get("id") == "submit"
    )
    assert re.search(
        r"goalCheck:\s*\{\s*enabled:\s*true,\s*maxRetries:\s*1\s*\}",
        dry_submit["run"],
    )
    assert "Make at most one focused refactoring." in dry_submit["run"]


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
    candidate_smoke = workflow["jobs"]["candidate-smoke"]
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

    assert candidate_smoke["needs"] == "build"
    assert candidate_smoke["strategy"]["matrix"]["arch"] == ["amd64", "arm64"]
    for job_name in ("build", "scan", "candidate-smoke", "publish"):
        assert workflow["jobs"][job_name]["environment"]["name"] == "docker"
    assert any(
        step.get("run") == "bash scripts/smoke-container-readiness.sh"
        for step in candidate_smoke["steps"]
    )
    assert publish["needs"] == ["build", "scan", "candidate-smoke"]
    promote = next(step for step in publish["steps"] if step.get("id") == "published-images")
    assert promote["name"] == "Promote and verify production image tags"
    assert promote["run"] == "bash scripts/promote-verified-images.sh"
    assert "${{ needs.build.outputs.image_ref }}" in promote["env"]["IMAGE_REF"]
    assert "${{ steps.meta.outputs.tags }}" in promote["env"]["DOCKER_METADATA_TAGS"]


def test_docker_publish_pins_buildx_and_runs_one_promote_verifier(workspace_root):
    """Keep the Buildx CLI stable and centralize promotion verification."""
    workflow = load_workflow(workspace_root, "docker-publish.yml")
    buildx_steps = [
        step
        for job in workflow["jobs"].values()
        for step in job.get("steps", [])
        if step.get("uses", "").startswith("docker/setup-buildx-action@")
    ]

    assert len(buildx_steps) == 2
    assert all(step["with"]["version"] == "v0.38.2" for step in buildx_steps)
    assert all(step["with"]["cache-binary"] is False for step in buildx_steps)

    publish_steps = workflow["jobs"]["publish"]["steps"]
    promote_step = next(step for step in publish_steps if step.get("id") == "published-images")
    checkout = next(
        step for step in publish_steps if step.get("name") == "Checkout promotion source"
    )
    assert checkout["uses"] == "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
    assert checkout["with"]["persist-credentials"] is False
    assert publish_steps.index(checkout) < publish_steps.index(promote_step)
    assert not any(
        step.get("name")
        in {
            "Promote verified image tags",
            "Verify promoted multi-architecture manifests",
        }
        for step in publish_steps
    )


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
    assert hub_login["with"]["username"] == "${{ vars.DOCKER_USERNAME }}"
    assert hub_login["with"]["password"] == "${{ secrets.DOCKER_PASSWORD }}"

    for job_name in ("verify", "build", "publish"):
        condition = workflow["jobs"][job_name]["if"]
        assert (
            "github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/main'"
            in condition
        )
        assert "github.event_name == 'release'" in condition


def test_release_verification_does_not_cache_untrusted_tag_dependencies(workspace_root):
    """Avoid cache-poisoning paths when verifying code from a published release tag."""
    workflow = load_workflow(workspace_root, "docker-publish.yml")
    steps = workflow["jobs"]["verify"]["steps"]

    python_setup = next(
        step for step in steps if step.get("uses", "").startswith("actions/setup-python@")
    )
    node_setup = next(
        step for step in steps if step.get("uses", "").startswith("actions/setup-node@")
    )
    assert "cache" not in python_setup["with"]
    assert node_setup["with"]["package-manager-cache"] is False


def test_release_settings_document_docker_environment_and_required_arm64_check(workspace_root):
    """Document the GitHub-side controls that YAML cannot configure itself."""
    guidance = (workspace_root / ".github" / "BRANCH_PROTECTION.md").read_text()

    assert "Container Runtime Smoke Test (amd64)" in guidance
    assert "Container Runtime Smoke Test (arm64)" in guidance
    assert "docker" in guidance
    assert "DOCKER_USERNAME" in guidance
    assert "DOCKER_PASSWORD" in guidance
    assert "Required reviewers" not in guidance
    assert "Deployment branch/tag rules" not in guidance
    ruleset_example = guidance.split("## Ruleset Example", maxsplit=1)[1]
    status_checks = ruleset_example.split("3. **Block force pushes**", maxsplit=1)[0]
    assert "`Container Runtime Smoke Test (amd64)`" in status_checks
    assert "`Container Runtime Smoke Test (arm64)`" in status_checks


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


def test_ci_and_release_use_shared_node_26_version(workspace_root):
    """Keep local npm policy and Node-based CI on the shared Node 26 baseline."""
    assert (workspace_root / ".nvmrc").read_text().strip() == "26"
    package = json.loads((workspace_root / "package.json").read_text())
    assert package["engines"]["node"] == ">=26"

    for filename in ("ci.yml", "docker-publish.yml"):
        workflow = load_workflow(workspace_root, filename)
        node_steps = [
            step
            for job in workflow["jobs"].values()
            for step in job.get("steps", [])
            if step.get("uses", "").startswith("actions/setup-node@")
        ]

        assert node_steps
        assert all(step.get("with", {}).get("node-version-file") == ".nvmrc" for step in node_steps)


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


def test_soyuz_dry_scopes_submission_token_to_submit_step(workspace_root):
    """Limit the Soyuz credential to the authenticated request step."""
    workflow = load_workflow(workspace_root, "kaseki-dry.yaml")
    job = workflow["jobs"]["dry_sweep"]
    assert "SOYUZ_SUBMISSION_API_TOKEN" not in job["env"]

    submit = next(step for step in job["steps"] if step.get("id") == "submit")
    assert submit["env"]["SOYUZ_SUBMISSION_API_TOKEN"] == (
        "${{ secrets.SOYUZ_SUBMISSION_API_TOKEN }}"
    )

    for step in job["steps"]:
        if step is not submit:
            assert "SOYUZ_SUBMISSION_API_TOKEN" not in step.get("env", {})


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
        index for index, step in enumerate(publish["steps"]) if step.get("id") == "published-images"
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


def test_codeql_manual_dispatch_is_limited_to_the_default_branch(workspace_root):
    """Keep a branch-edited CodeQL workflow away from its security-events write token."""
    workflow = load_workflow(workspace_root, "codeql.yml")
    analyze = workflow["jobs"]["analyze"]

    assert analyze["if"] == (
        "github.event_name != 'workflow_dispatch' || "
        "github.ref == format('refs/heads/{0}', github.event.repository.default_branch)"
    )
    assert analyze["permissions"]["security-events"] == "write"


def test_required_checks_cover_dependency_resolution_docs_and_container_smokes(workspace_root):
    """Document stable checks for the additional PR validation jobs."""
    guidance = (workspace_root / ".github" / "BRANCH_PROTECTION.md").read_text()
    required_checks = (
        "Runtime Dependency Resolution",
        "Dependency Review",
        "Documentation Check",
        "Container Runtime Smoke Test (amd64)",
        "Container Runtime Smoke Test (arm64)",
    )

    for check in required_checks:
        assert guidance.count(f"`{check}`") >= 2


def test_release_tag_ruleset_matches_the_supported_release_tag_format(workspace_root):
    """Protect the two-component vX.Y tags accepted by the release workflow."""
    guidance = (workspace_root / ".github" / "BRANCH_PROTECTION.md").read_text()

    assert "`v*.*`" in guidance
    assert "`v*.*.*`" not in guidance


def test_ci_runs_pinned_workflow_and_dependency_security_checks(workspace_root):
    """Lint workflow security and review dependency changes without write permissions."""
    workflow = load_workflow(workspace_root, "ci.yml")
    lint = workflow["jobs"]["lint"]
    zizmor = next(
        step for step in lint["steps"] if step.get("name") == "Analyze GitHub Actions security"
    )
    assert re.fullmatch(r"zizmorcore/zizmor-action@[0-9a-f]{40}", zizmor["uses"])
    assert zizmor["with"]["version"] == "1.32.0"
    assert zizmor["with"]["advanced-security"] is False
    assert zizmor["with"]["annotations"] is True
    assert zizmor["with"]["online-audits"] is False

    review = workflow["jobs"]["dependency-review"]
    action = next(
        step
        for step in review["steps"]
        if step.get("uses", "").startswith("actions/dependency-review-action@")
    )
    assert review["if"] == "github.event_name == 'pull_request'"
    assert review["permissions"] == {"contents": "read"}
    assert re.fullmatch(r"actions/dependency-review-action@[0-9a-f]{40}", action["uses"])
    assert action["with"]["fail-on-severity"] == "high"
    assert action["with"]["fail-on-scopes"] == "runtime, development, unknown"


def test_ci_audits_all_python_runtime_requirement_sets(workspace_root):
    """Audit optional integrations as well as dependencies in the default image."""
    workflow = load_workflow(workspace_root, "ci.yml")
    security_steps = workflow["jobs"]["security"]["steps"]
    audit = next(step for step in security_steps if step.get("name") == "Audit Python dependencies")

    assert "python -m pip_audit" in audit["run"]
    assert '--cache-dir "$RUNNER_TEMP/pip-audit-cache"' in audit["run"]
    for requirement_file in (
        "requirements.txt",
        "requirements-sentry.txt",
        "requirements-rate-limiter.txt",
    ):
        assert requirement_file in audit["run"]

    requirements = (workspace_root / "requirements-security.txt").read_text()
    assert re.search(r"(?m)^pip-audit==[0-9]+\.[0-9]+\.[0-9]+$", requirements)


def test_ci_builds_docs_and_validates_mermaid_diagrams(workspace_root):
    """Run the existing Sphinx and Mermaid checks in pull request CI."""
    workflow = load_workflow(workspace_root, "ci.yml")
    docs_steps = workflow["jobs"]["documentation"]["steps"]

    python_setup = next(
        step for step in docs_steps if step.get("uses", "").startswith("actions/setup-python@")
    )
    assert python_setup["with"]["python-version"] == "3.12"

    assert any(step.get("run") == "make docs-check" for step in docs_steps)
    assert any("make validate-diagrams" in step.get("run", "") for step in docs_steps)
    install_docs = next(
        step for step in docs_steps if step.get("name") == "Install documentation dependencies"
    )
    assert "requirements-docs.txt" in install_docs["run"]
    pinned_requirements = [
        line.strip()
        for line in (workspace_root / "requirements-docs.txt").read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert pinned_requirements
    assert all("==" in line for line in pinned_requirements)

    makefile = (workspace_root / "Makefile").read_text()
    assert "$(PIP) install -r requirements-docs.txt" in makefile


def test_security_scan_smokes_mock_camera_containers_on_both_architectures(workspace_root):
    """Exercise the built application image on native AMD64 and emulated ARM64."""
    workflow = load_workflow(workspace_root, "security-scan.yml")
    smoke = workflow["jobs"]["container-smoke"]

    assert smoke["name"] == "Container Runtime Smoke Test (${{ matrix.arch }})"
    assert smoke["strategy"]["matrix"]["arch"] == ["amd64", "arm64"]
    assert any(step.get("if") == "matrix.arch == 'arm64'" for step in smoke["steps"])
    build = next(step for step in smoke["steps"] if step.get("name") == "Build mock-camera image")
    readiness = next(
        step for step in smoke["steps"] if step.get("name") == "Start container and check readiness"
    )
    assert "--tag motion-in-ocean:runtime-smoke-${{ matrix.arch }} ." in build["run"]
    assert readiness["env"]["IMAGE_REF"] == "motion-in-ocean:runtime-smoke-${{ matrix.arch }}"
    assert any(
        step.get("run") == "bash scripts/smoke-container-readiness.sh" for step in smoke["steps"]
    )


def test_runtime_dependency_matrix_has_a_stable_required_gate(workspace_root):
    """Expose one branch-protection check after every Python/platform matrix cell passes."""
    workflow = load_workflow(workspace_root, "ci.yml")
    gate = workflow["jobs"]["runtime-dependency-resolution-gate"]

    assert gate["name"] == "Runtime Dependency Resolution"
    assert gate["needs"] == "runtime-dependency-resolution"
    assert gate["if"] == "always()"
    assert gate["steps"]
