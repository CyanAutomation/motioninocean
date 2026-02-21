#!/usr/bin/env python3
"""
Architecture-aware stack validation for motion-in-ocean.

This script validates the required Python stack based on the build architecture:
- arm64: Validates full camera stack (numpy, flask, flask_cors, picamera2)
- amd64: Validates Python stack only (numpy, flask, flask_cors)
"""

import os
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


def main():
    """Main entry point for stack validation."""
    targetarch = os.environ.get("TARGETARCH", "unknown")

    if targetarch == "arm64":
        return validate_arm64()
    elif targetarch == "amd64":
        return validate_amd64()
    else:
        print(f"ERROR: Unknown or missing TARGETARCH: {targetarch}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
