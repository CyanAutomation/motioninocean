"""Contract tests for the manual motioninocean Cloud Run demo build."""

from pathlib import Path

import yaml


def test_cloudbuild_deploys_short_sha_tag_in_europe_west1_with_public_demo_limits():
    """The demo build uses Cloud Build's commit SHA and bounded service settings."""
    cloudbuild_path = Path(__file__).resolve().parents[1] / "cloudbuild.yaml"
    cloudbuild_content = cloudbuild_path.read_text()
    config = yaml.safe_load(cloudbuild_content)
    steps = {step["id"]: step for step in config["steps"]}
    substitutions = config["substitutions"]

    assert substitutions["_GAR_REGION"] == "europe-west1"
    assert substitutions["_CLOUD_RUN_REGION"] == "europe-west1"
    assert "_REVISION" not in substitutions
    build_script = steps["build-and-push"]["args"][-1]
    assert "--file Dockerfile" in build_script
    assert "--platform linux/amd64" in build_script
    assert build_script.count("$${IMAGE_BASE}") == 4
    assert '"$${IMAGE_BASE}:${_IMAGE_TAG}"' in build_script
    assert '"$${IMAGE_BASE}:$SHORT_SHA"' in build_script
    assert '--build-arg VCS_REF="$SHORT_SHA"' in build_script
    assert "_REVISION" not in cloudbuild_content

    deploy_args = steps["deploy-cloud-run"]["args"]
    assert deploy_args[deploy_args.index("--region") + 1] == "${_CLOUD_RUN_REGION}"
    image_arg = deploy_args[deploy_args.index("--image") + 1]
    assert image_arg.endswith(":$SHORT_SHA")
    assert "--allow-unauthenticated" in deploy_args
    assert "--port" in deploy_args
    assert "--max" in deploy_args
    assert "--concurrency" in deploy_args
    assert "--timeout" in deploy_args
    env_vars = deploy_args[deploy_args.index("--set-env-vars") + 1]
    assert "MIO_MOCK_CAMERA=true" in env_vars
    assert "MIO_DEMO_READ_ONLY=true" in env_vars
    assert "MIO_BIND_HOST=0.0.0.0" in env_vars
    assert "MIO_PORT=8080" in env_vars
