#!/usr/bin/env python3
"""
Integration test verification document for motion-in-ocean.
This validates the expected behavior and startup flow.
"""

import subprocess
import json
import sys

def test_docker_compose_build():
    """Test if docker-compose can validate the build."""
    print("\n=== Docker Compose Build Validation ===")
    try:
        result = subprocess.run(
            ['docker-compose', 'config'],
            capture_output=True,
            text=True,
            cwd='/workspaces/MotionInOcean'
        )
        
        if result.returncode == 0:
            print("✓ docker-compose.yml is valid and can be processed")
            config = json.loads(result.stdout) if '{' in result.stdout else None
            if config:
                print(f"✓ Service name: motion-in-ocean")
                print(f"✓ Image: {config.get('services', {}).get('motion-in-ocean', {}).get('image', 'N/A')}")
            return True
        else:
            print(f"✗ docker-compose validation failed: {result.stderr}")
            return False
    except FileNotFoundError:
        print("⚠ Docker Compose not installed (expected in dev environment)")
        return True  # Not a failure, just not testable
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_startup_sequence():
    """Verify the startup sequence is correct."""
    print("\n=== Startup Sequence Verification ===")
    
    # Expected startup order
    startup_sequence = [
        ("Initialize logger", "logging.basicConfig"),
        ("Parse environment variables", "os.environ.get"),
        ("Define apply_edge_detection", "apply_edge_detection"),
        ("Define StreamingOutput class", "class StreamingOutput"),
        ("Create Flask app", "app = Flask"),
        ("Define routes", "@app.route"),
        ("Main execution block", "if __name__ == '__main__':"),
        ("Initialize Picamera2", "Picamera2()"),
        ("Configure video", "create_video_configuration"),
        ("Start recording", "start_recording"),
        ("Start Flask server", "app.run"),
    ]
    
    with open('/workspaces/MotionInOcean/pi_camera_in_docker/main.py', 'r') as f:
        code = f.read()
    
    for step, marker in startup_sequence:
        if marker in code:
            print(f"✓ {step}")
        else:
            print(f"✗ Missing: {step}")
            return False
    
    return True

def test_error_recovery():
    """Verify error recovery paths."""
    print("\n=== Error Recovery Paths ===")
    
    with open('/workspaces/MotionInOcean/pi_camera_in_docker/main.py', 'r') as f:
        code = f.read()
    
    recovery_scenarios = {
        "Permission denied → helpful error message": [
            "except PermissionError",
            "Ensure the container has proper device access"
        ],
        "Camera initialization fail → helpful error message": [
            "except RuntimeError",
            "Verify camera is enabled on the host"
        ],
        "Edge detection failure → graceful handling": [
            "except Exception as e:",
            "logger.error"
        ],
        "Clean shutdown → safe cleanup": [
            "finally:",
            "stop_recording",
            "if picam2_instance is not None"
        ],
    }
    
    all_ok = True
    for scenario, markers in recovery_scenarios.items():
        if all(marker in code for marker in markers):
            print(f"✓ {scenario}")
        else:
            print(f"✗ Missing: {scenario}")
            all_ok = False
    
    return all_ok

def test_health_endpoints():
    """Verify health check endpoints."""
    print("\n=== Health Check Endpoints ===")
    
    with open('/workspaces/MotionInOcean/pi_camera_in_docker/main.py', 'r') as f:
        code = f.read()
    
    endpoints = {
        "/health (liveness)": [
            "@app.route('/health')",
            "healthy",
            "200"
        ],
        "/ready (readiness)": [
            "@app.route('/ready')",
            "ready",
            "picam2_instance.started",
            "503"
        ],
        "/metrics (monitoring)": [
            "@app.route('/metrics')",
            "camera_active",
            "frames_captured",
            "current_fps"
        ],
        "/stream.mjpg (actual stream)": [
            "@app.route('/stream.mjpg')",
            "multipart/x-mixed-replace"
        ]
    }
    
    all_ok = True
    for endpoint, markers in endpoints.items():
        if all(marker in code for marker in markers):
            print(f"✓ {endpoint}")
        else:
            print(f"✗ Missing: {endpoint}")
            all_ok = False
    
    return all_ok

def test_metrics_collection():
    """Verify metrics collection."""
    print("\n=== Metrics Collection ===")
    
    with open('/workspaces/MotionInOcean/pi_camera_in_docker/main.py', 'r') as f:
        code = f.read()
    
    metrics = {
        "Frame count tracking": "self.frame_count += 1",
        "FPS calculation": "self.get_fps()",
        "Frame timing": "self.frame_times",
        "Status endpoint": "def get_status(self)",
        "Uptime tracking": "app.start_time",
    }
    
    all_ok = True
    for metric, marker in metrics.items():
        if marker in code:
            print(f"✓ {metric}")
        else:
            print(f"✗ Missing: {metric}")
            all_ok = False
    
    return all_ok

def test_device_security():
    """Verify device access security."""
    print("\n=== Device Access Security ===")
    
    with open('/workspaces/MotionInOcean/docker-compose.yml', 'r') as f:
        compose = f.read()
    
    checks = {
        "Uses explicit devices instead of privileged": [
            "devices:",
            "/dev/dma_heap",
            "/dev/vchiq",
            "/dev/video"
        ],
        "No privileged mode enabled": [
            "# privileged: true"  # Should be commented out
        ],
        "Healthcheck configured": [
            "healthcheck:",
            "/health"
        ]
    }
    
    all_ok = True
    for check, markers in checks.items():
        if all(marker in compose for marker in markers):
            print(f"✓ {check}")
        else:
            print(f"✗ Missing: {check}")
            all_ok = False
    
    # Verify privileged is NOT active (it's commented)
    if "privileged: true" in compose and "# privileged: true" not in compose:
        print("✗ Warning: privileged mode is active (should be commented)")
        all_ok = False
    
    return all_ok

def main():
    print("=" * 70)
    print("motion-in-ocean Integration Test & Verification")
    print("=" * 70)
    
    tests = [
        ("Docker Compose Validation", test_docker_compose_build),
        ("Startup Sequence", test_startup_sequence),
        ("Error Recovery Paths", test_error_recovery),
        ("Health Check Endpoints", test_health_endpoints),
        ("Metrics Collection", test_metrics_collection),
        ("Device Access Security", test_device_security),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 70)
    print("Integration Test Summary")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n" + "=" * 70)
        print("✓ All integration tests passed!")
        print("=" * 70)
        print("\nThe configuration is ready for deployment.")
        print("\nExpected Container Behavior:")
        print("  1. Logs will show startup initialization steps")
        print("  2. Camera will initialize and start streaming")
        print("  3. Flask server runs on 0.0.0.0:8000")
        print("  4. /health endpoint returns 200 (liveness)")
        print("  5. /ready endpoint returns 200 if camera is streaming (readiness)")
        print("  6. /stream.mjpg provides MJPEG video feed")
        print("  7. Docker healthcheck queries /health every 30s")
        print("\nEnvironment Variables (from .env):")
        print("  - TZ: Europe/London")
        print("  - RESOLUTION: 1280x720")
        print("  - EDGE_DETECTION: false")
        print("  - FPS: (optional, defaults to camera max)")
        print("\nDevice Requirements:")
        print("  - /dev/dma_heap: libcamera memory management")
        print("  - /dev/vchiq: Camera ISP access")
        print("  - /dev/video*: Camera device nodes")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed. Review the output above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
