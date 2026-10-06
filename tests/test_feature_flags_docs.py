"""Documentation contract tests for feature flags."""

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FEATURE_FLAGS_DOC_PATH = REPO_ROOT / "docs/guides/FEATURE_FLAGS.md"


def _documented_flag_names() -> set[str]:
    """Extract canonical feature-flag names from docs headings."""
    content = FEATURE_FLAGS_DOC_PATH.read_text(encoding="utf-8")
    return set(re.findall(r"^### `MIO_([A-Z0-9_]+)`", content, flags=re.MULTILINE))


def test_feature_flag_guide_matches_the_runtime_registry() -> None:
    """Document all runtime flags used by the backend.

    Traceability: docs/product/PRD-backend.md#4-environment-driven-configuration-p1.
    """
    from pi_camera_in_docker.feature_flags import ACTIVE_RUNTIME_FLAGS, FeatureFlags

    runtime_flags = set(FeatureFlags().get_all_flags())

    assert runtime_flags == set(ACTIVE_RUNTIME_FLAGS)
    assert _documented_flag_names() == runtime_flags
