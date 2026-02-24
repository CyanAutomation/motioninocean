"""Documentation contract tests for feature flags."""

import re
from pathlib import Path

from pi_camera_in_docker.feature_flags import FeatureFlags


FEATURE_FLAGS_DOC_PATH = Path("docs/guides/FEATURE_FLAGS.md")


def _documented_flag_names() -> set[str]:
    """Extract canonical feature-flag names from docs headings."""
    content = FEATURE_FLAGS_DOC_PATH.read_text(encoding="utf-8")
    return set(re.findall(r"^### `MIO_([A-Z0-9_]+)`", content, flags=re.MULTILINE))


def _documented_legacy_aliases() -> dict[str, str]:
    """Extract documented legacy alias mappings from docs bullets."""
    content = FEATURE_FLAGS_DOC_PATH.read_text(encoding="utf-8")
    return dict(
        re.findall(
            r"^- `([A-Z0-9_]+)` → `MIO_([A-Z0-9_]+)`$",
            content,
            flags=re.MULTILINE,
        )
    )


def test_feature_flags_docs_match_registry_flags() -> None:
    """Documented canonical flags should match the runtime flag registry."""
    documented = _documented_flag_names()

    registry = FeatureFlags()
    registered = set(registry.get_all_flags().keys())

    assert documented == registered


def test_feature_flags_docs_match_supported_legacy_aliases() -> None:
    """Documented aliases should match legacy aliases still wired in registry."""
    documented_aliases = _documented_legacy_aliases()

    registry = FeatureFlags()
    supported_aliases: dict[str, str] = {}
    for flag_name, flag_info in registry.get_all_flag_info().items():
        for alias in flag_info.get("backward_compat_vars", []):
            supported_aliases[alias] = flag_name

    assert documented_aliases == supported_aliases
