---
name: cloud-run-demo
description: Build, deploy, and verify the public mock-camera demo on Google Cloud Run. Use for changes to the manual Cloud Build demo or when checking its read-only behavior and runtime limits.
owner: motion-in-ocean team
last-reviewed: 2026-11-15
category: Deployment
compatible-repo-areas:
  - cloudbuild.yaml
  - docs/guides/CLOUD_RUN_DEMO.md
  - tests/test_cloudrun_contract.py
  - tests/integration/test_demo_read_only.py
---

## Purpose

Deploy and verify the public mock-camera demo with its documented read-only boundary and bounded Cloud Run capacity.

## Scope and trigger conditions

- Use when changing, deploying, or validating the manual Cloud Build configuration for the public Cloud Run demo.
- This workflow deploys only the mock-camera demo. Use [`release-operator`](../release-operator/SKILL.md) for production GHCR and Docker Hub releases.
- Do not use the public demo for real camera feeds, private configuration, or production workload data.

## Required inputs

- A clean checkout and permission to submit a Cloud Build and deploy the Cloud Run service.
- A Google Cloud project with Cloud Build, Artifact Registry, and Cloud Run enabled.
- The Artifact Registry repository and service account permissions described in `docs/guides/CLOUD_RUN_DEMO.md`.

## Step-by-step workflow

1. Read [`docs/guides/CLOUD_RUN_DEMO.md`](../../../docs/guides/CLOUD_RUN_DEMO.md) and inspect `cloudbuild.yaml` before changing project, region, identity, service, or runtime settings.
2. For a source change, update the contract tests alongside the build configuration. Preserve the mock-camera and read-only settings, SHA-tagged deployment, and bounded instance/concurrency settings.
3. Run the focused contract and read-only tests:

   ```bash
   .venv/bin/python -m pytest tests/test_cloudrun_contract.py tests/integration/test_demo_read_only.py -q
   ```

4. Before submitting a build, confirm the checkout is clean and the active Google Cloud project and region are correct:

   ```bash
   test -z "$(git status --porcelain)"
   gcloud config get-value project
   ```

5. Submit the manual build from the repository root:

   ```bash
   gcloud builds submit --config cloudbuild.yaml .
   ```

6. Inspect the Cloud Build log and deployed Cloud Run revision. Confirm it uses the immutable short-SHA image tag and the expected service, region, port, resource limits, and environment variables.
7. Open the service URL and verify the simulated stream works. Confirm read requests work and mutation requests return HTTP 403; confirm the UI identifies the stream as simulated and hides settings/setup controls.
8. Record the deployed revision, service URL, test results, and any remaining deployment limitations.

## Validation checklist

- [ ] Contract tests preserve the configured image tag, region, public access choice, and capacity limits.
- [ ] The deployed revision uses the short-SHA image tag from the submitted source.
- [ ] The stream is simulated and no physical camera or remote node is required.
- [ ] Write requests are rejected with HTTP 403 and the demo UI does not expose setup or settings controls.
- [ ] The deployment uses the documented port, concurrency, instance, CPU, memory, and request-timeout settings.
- [ ] The service is not used for real camera feeds, secrets, or production data.
- [ ] The Cloud Run guide and contract tests agree with `cloudbuild.yaml`.

## Source of truth

- `cloudbuild.yaml` — Build tags, deployment settings, and runtime environment.
- `docs/guides/CLOUD_RUN_DEMO.md` — Google Cloud setup, permissions, deployment, demo limits, and verification.
- `tests/test_cloudrun_contract.py` — Static contract for the Cloud Build configuration.
- `tests/integration/test_demo_read_only.py` — Read-only HTTP behavior.
- `Dockerfile` — The image build used for the amd64 demo.

## Common failure modes and recovery actions

- **Failure:** Cloud Build cannot push or deploy. **Recovery:** Check the documented Artifact Registry and Cloud Run service-account permissions; keep permissions scoped to the demo resources.
- **Failure:** The wrong image revision is running. **Recovery:** Compare the deployed image tag with the submitted build's short commit SHA and inspect the Cloud Build log.
- **Failure:** A mutation request succeeds. **Recovery:** Treat this as a release blocker; restore `MIO_DEMO_READ_ONLY=true` and investigate the application-wide guard before redeploying.
- **Failure:** The service is unavailable under stream load. **Recovery:** Check Cloud Run instance/concurrency limits, request timeout, and browser reconnect behavior against the documented limits.
- **Failure:** The service exposes real camera data or sensitive configuration. **Recovery:** Disable public access immediately and replace it with a private deployment; the public demo is for mock content only.

## Related Skills

- [`deployment-validation-health-checks`](../deployment-validation-health-checks/SKILL.md) — Validate Compose webcam and management deployments.
- [`ci-triage`](../ci-triage/SKILL.md) — Diagnose CI or container-scan failures associated with a change.
- [`release-operator`](../release-operator/SKILL.md) — Publish production container images through a GitHub Release.

## Maintenance notes

Review this skill when `cloudbuild.yaml`, the Cloud Run guide, demo read-only behavior, or Cloud Run contract tests change.
