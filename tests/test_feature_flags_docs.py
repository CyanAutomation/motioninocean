"""Documentation contract tests for feature flags."""

import re
from pathlib import Path

from pi_camera_in_docker.feature_flags import FeatureFlags


FEATURE_FLAGS_DOC_PATH = Path("docs/guides/FEATURE_FLAGS.md")


def _documented_flag_names() -> set[str]:
    """Extract canonical feature-flag names from docs headings."""
    content = FEATURE_FLAGS_DOC_PATH.read_text(encoding="utf-8")
    return set(re.findall(r"^### `MIO_([A-Z0-9_]+)`", content, flags=re.MULTILINE))
