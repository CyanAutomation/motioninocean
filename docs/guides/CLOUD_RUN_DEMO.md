# Google Cloud Run Demo

Motion In Ocean can run as a public, mock-camera demo on Cloud Run. This demo uses
the existing Dockerfile's `linux/amd64` path, which omits Raspberry Pi camera
packages, and sets `MIO_MOCK_CAMERA=true`. It does not connect to a physical
camera or manage remote webcam nodes.

## One-time Google Cloud setup

Choose a Google Cloud project and enable the required services:

```bash
gcloud config set project YOUR_PROJECT_ID
gcloud services enable cloudbuild.googleapis.com artifactregistry.googleapis.com run.googleapis.com
gcloud artifacts repositories create motioninocean-demo \
  --repository-format=docker \
  --location=europe-west1 \
  --description="Motion In Ocean Cloud Run demo images"
```

Grant the Cloud Build service account permission to write to this Artifact
Registry repository and deploy the Cloud Run service. The identity used to deploy
also needs permission to act as the Cloud Run runtime service account. Keep these
roles scoped to the demo repository and service where the project allows it.

## Build and deploy

The checked-in [cloudbuild.yaml](../../cloudbuild.yaml) is manual only. It builds
and pushes a demo tag and an immutable git-SHA tag, then deploys that SHA tag to
Cloud Run. Run it from a clean checkout so the tag identifies the source being
built. Both Artifact Registry and Cloud Run default to `europe-west1`.

```bash
test -z "$(git status --porcelain)"
REVISION="$(git rev-parse --short=12 HEAD)"
gcloud builds submit --config cloudbuild.yaml \
  --substitutions="_REVISION=${REVISION}" .
```

The Cloud Run service is public and unauthenticated so visitors can open the
HTTPS service URL. The deployment sets `MIO_DEMO_READ_ONLY=true`: GET, HEAD, and
OPTIONS requests work, while write methods return HTTP 403. The stream page hides
the settings and setup tabs and labels the simulated stream. Keep the service
private instead by removing `--allow-unauthenticated` and granting Cloud Run
invoker access only to the intended reviewers.

The service has zero minimum and two maximum instances, four requests per
instance, one vCPU, 512 MiB memory, and a one-hour request timeout for MJPEG
streams. It caps the mock stream at 10 FPS and three clients per instance. Active
streams consume instance capacity until they close or reach the Cloud Run request
timeout. The browser closes the stream while its tab is hidden and reconnects
after transient failures.

## Runtime behavior and limits

- The container listens on `0.0.0.0:8080`; the app uses Cloud Run's injected
  `PORT` as a fallback when `MIO_PORT` is not set.
- Gunicorn runs one `gthread` worker with eight threads per instance. Its
  60-second worker timeout monitors the worker heartbeat, not individual request
  duration; Cloud Run's one-hour request timeout governs active MJPEG streams.
- Runtime settings use `/tmp/application-settings.json`. Cloud Run storage is
  temporary and per instance; changes do not persist across restarts or scaling.
  In this demo, write endpoints are disabled regardless.
- `MIO_WEBCAM_CONTROL_PLANE_AUTH_TOKEN` is intentionally unset so the browser
  can read stream status and Cloud Run health checks can read health endpoints.
  The read-only demo guard blocks mutations across the whole Flask app.
- This public service has no user login. Do not use it for real camera feeds,
  private configuration, or production workload data.

The GitHub release workflow remains responsible for production GHCR and Docker
Hub images. This Cloud Build config deploys only the public mock demo.
