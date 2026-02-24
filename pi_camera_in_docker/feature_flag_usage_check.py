"""Validate that every registered feature flag is consumed by runtime code."""

import sys

from pi_camera_in_docker.feature_flags import ACTIVE_RUNTIME_FLAGS, FeatureFlags


def _emit(line: str) -> None:
    """Write a status line to stdout.

    Args:
        line: Line to emit.
    """
    sys.stdout.write(f"{line}\n")


def main() -> int:
    """Run runtime-usage validation for feature flags.

    Returns:
        Process exit code (0 on success, 1 on validation failure).
    """
    registry = set(FeatureFlags().get_all_flags().keys())
    active = set(ACTIVE_RUNTIME_FLAGS)

    unknown_active = sorted(active - registry)
    missing_runtime_reads = sorted(registry - active)

    if unknown_active:
        _emit("ACTIVE_RUNTIME_FLAGS contains unknown flags:")
        for name in unknown_active:
            _emit(f"  - {name}")

    if missing_runtime_reads:
        _emit(
            "Registered feature flags without runtime reads. "
            "Add runtime usage and update ACTIVE_RUNTIME_FLAGS:"
        )
        for name in missing_runtime_reads:
            _emit(f"  - {name}")

    if unknown_active or missing_runtime_reads:
        return 1

    _emit(f"Feature flag runtime usage check passed ({len(registry)} flags).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
