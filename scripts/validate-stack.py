#!/usr/bin/env python3
"""
Architecture-aware stack validation for motion-in-ocean.

This script validates the required Python stack based on the build architecture:
- arm64: Validates full camera stack (numpy, flask, flask_cors, picamera2)
- amd64: Validates Python stack only (numpy, flask, flask_cors)
"""

import os
import platform
import subprocess
import sys


def validate_arm64():
    """Validate full camera stack for ARM64 Raspberry Pi builds."""
    try:
        import numpy
        import flask
        import flask_cors
        import picamera2

        # Validate picamera2 API contract
        module_fn = getattr(picamera2, "global_camera_info", None)
        picamera2_class = getattr(picamera2, "Picamera2", None)
        class_fn = (
            getattr(picamera2_class, "global_camera_info", None)
            if picamera2_class is not None
            else None
        )

        if callable(module_fn):
            print(
                "ARM64 camera stack validation passed; "
                "camera-info API via picamera2.global_camera_info"
            )
            return 0
        elif callable(class_fn):
            print(
                "ARM64 camera stack validation passed; "
                "camera-info API via Picamera2.global_camera_info"
            )
            return 0
        else:
            print(
                "ERROR: Incompatible python3-picamera2 package revision: "
                "expected picamera2.global_camera_info or "
                "picamera2.Picamera2.global_camera_info"
            )
            return 1
    except ImportError as e:
        print(f"ERROR: Failed to import required camera modules: {e}")
        return 1


def validate_amd64():
    """Validate Python stack for AMD64 mock camera builds."""
    try:
        import numpy
        import flask
        import flask_cors

        print(
            "AMD64 mock build: core Python stack validation passed; "
            "picamera2/libcamera not required"
        )
        return 0
    except ImportError as e:
        print(f"ERROR: Failed to import required Python modules: {e}")
        return 1


from typing import Optional

def _normalize_architecture(value: Optional[str]) -> Optional[str]:
    """Normalize architecture labels used by this script."""
    if value is None:
        return None

    mapping = {
        "aarch64": "arm64",
        "amd64": "amd64",
        "arm64": "arm64",
        "x86_64": "amd64",
    }
    return mapping.get(value.strip().lower())


def _detect_architecture_from_dpkg() -> str | None:
    """Detect architecture from the container OS using dpkg."""
    try:
        result = subprocess.run(
            ["dpkg", "--print-architecture"],
            capture_output=True,
            check=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None

    return _normalize_architecture(result.stdout)


def _select_target_architecture() -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Determine architecture from dpkg first, then env var, then platform.machine."""
    dpkg_arch = _detect_architecture_from_dpkg()
    env_arch = _normalize_architecture(os.environ.get("TARGETARCH"))
    machine_arch = _normalize_architecture(platform.machine())

    selected_arch = dpkg_arch or env_arch or machine_arch
    return selected_arch, dpkg_arch, env_arch or machine_arch


def main():
    """Main entry point for stack validation."""
    targetarch, detected_arch, fallback_arch = _select_target_architecture()

    if targetarch == "arm64":
        return validate_arm64()
    elif targetarch == "amd64":
        return validate_amd64()
    else:
        print(
            "ERROR: Unknown architecture. "
            f"detected_from_dpkg={detected_arch or 'unknown'}, "
            f"fallback_value={fallback_arch or 'unknown'}"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
