#!/usr/bin/env python3
"""
Simple test to verify the /metrics endpoint returns the expected JSON structure
"""

import json
import sys

# Read the main.py file to extract the metrics endpoint structure
with open('/workspaces/MotionInOcean/pi_camera_in_docker/main.py', 'r') as f:
    content = f.read()

# Check for required fields in the metrics endpoint
required_fields = [
    '"camera_active"',
    '"frames_captured"',
    '"current_fps"',
    '"uptime_seconds"',
    '"resolution"',
    '"edge_detection"',
    '"timestamp"'
]

print("=" * 70)
print("Testing /metrics endpoint structure")
print("=" * 70)
print()

all_present = True
for field in required_fields:
    if field in content:
        # Find the context around this field
        idx = content.find(field)
        # Check if it's within the metrics route
        metrics_start = content.find('@app.route(\'/metrics\')')
        next_route = content.find('@app.route', metrics_start + 10)
        
        if metrics_start < idx < next_route:
            print(f"✓ Field {field} present in /metrics endpoint")
        else:
            print(f"✗ Field {field} found but not in /metrics endpoint")
            all_present = False
    else:
        print(f"✗ Field {field} not found")
        all_present = False

print()
print("=" * 70)

# Verify the endpoint is defined
if '@app.route(\'/metrics\')' in content:
    print("✓ /metrics endpoint is defined")
else:
    print("✗ /metrics endpoint is not defined")
    all_present = False

# Check it returns JSON
if 'jsonify' in content[content.find('@app.route(\'/metrics\')'):content.find('@app.route(\'/metrics\')') + 500]:
    print("✓ /metrics endpoint returns JSON")
else:
    print("✗ /metrics endpoint doesn't return JSON")
    all_present = False

print("=" * 70)
print()

if all_present:
    print("✅ All required fields are present in /metrics endpoint")
    print()
    print("Expected JSON structure:")
    print(json.dumps({
        "camera_active": True,
        "frames_captured": 1234,
        "current_fps": 25.5,
        "uptime_seconds": 120.5,
        "resolution": [1280, 720],
        "edge_detection": False,
        "timestamp": "2026-01-20T12:00:00.000000"
    }, indent=2))
    sys.exit(0)
else:
    print("❌ Some required fields are missing")
    sys.exit(1)
