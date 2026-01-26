#!/bin/bash
# detect-devices.sh - Raspberry Pi Camera Device Detection Helper
# Helps identify which devices exist on your system for docker-compose.yml configuration

set -e

# Arrays to store detected devices
CORE_DEVICES=()
MEDIA_DEVICES=()
VIDEO_DEVICES=()

echo "🔍 motion-in-ocean - Camera Device Detection"
echo "=========================================="
echo ""

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ]; then
    echo "⚠️  Warning: Not running on Raspberry Pi hardware"
    echo "This script is designed for Raspberry Pi systems."
    echo ""
fi

# Check for required core devices
echo "📋 Core Devices (Required):"
echo ""

check_device() {
    local device_path=$1
    local description=$2
    if [ -e "$device_path" ]; then
        echo "  ✓ $device_path - $description"
        ls -l "$device_path" | awk '{print "    Permissions:", $1, "Owner:", $3":"$4}'
        CORE_DEVICES+=("$device_path")
        return 0
    else
        echo "  ✗ $device_path - $description (NOT FOUND)"
        return 1
    fi
}

# Core devices
if [ -d "/dev/dma_heap" ]; then
    echo "  ✓ /dev/dma_heap - Memory management for libcamera (directory)"
    ls -l /dev/dma_heap/ 2>/dev/null | awk '/^[c|l]/ {print "    " $0}'
    CORE_DEVICES+=("/dev/dma_heap")
elif [ -e "/dev/dma_heap" ]; then
    check_device "/dev/dma_heap" "Memory management for libcamera"
else
    echo "  ✗ /dev/dma_heap - Memory management for libcamera (NOT FOUND)"
fi
check_device "/dev/vchiq" "VideoCore Host Interface"

echo ""
echo "� Media Controller Devices (Required for libcamera):"  
echo ""

# Use a glob to find media devices
for device in /dev/media*; do
    if [ -e "$device" ]; then
        echo "  ✓ $device"
        ls -l "$device" | awk '{print "    Permissions:", $1, "Owner:", $3":"$4}'
        MEDIA_DEVICES+=("$device")
    fi
done

if [ ${#MEDIA_DEVICES[@]} -eq 0 ]; then
    echo "  ✗ No /dev/media* devices found"
    echo ""
    echo "  Troubleshooting:"
    echo "  1. Ensure camera is enabled: sudo raspi-config"
    echo "  2. Check if camera driver is loaded: lsmod | grep bcm2835"
    echo "  3. Reboot after enabling camera"
fi

echo ""
echo "�📹 Video Devices (Camera Nodes):"
echo ""

# Use a glob to find video devices
for device in /dev/video*; do
    if [ -e "$device" ]; then
        echo "  ✓ $device"
        ls -l "$device" | awk '{print "    Permissions:", $1, "Owner:", $3":"$4}'
        VIDEO_DEVICES+=("$device")
    fi
done

if [ ${#VIDEO_DEVICES[@]} -eq 0 ]; then
    echo "  ✗ No /dev/video* devices found"
    echo ""
    echo "  Troubleshooting:"
    echo "  1. Ensure camera is enabled: sudo raspi-config"
    echo "  2. Check camera connection and reboot"
    echo "  3. Test with: rpicam-hello --list-cameras"
fi

echo ""
echo "🔧 Recommended docker-compose.yml Configuration:"
echo ""
echo "devices:"
for device in "${CORE_DEVICES[@]}"; do
    echo "  - $device:$device"
done
for device in "${MEDIA_DEVICES[@]}"; do
    echo "  - $device:$device"
done
for device in "${VIDEO_DEVICES[@]}"; do
    echo "  - $device:$device"
done

echo ""
echo "📝 Alternative: Use device_cgroup_rules (automatically allows all matching devices):"
echo ""
echo "device_cgroup_rules:"
echo "  - 'c 253:* rmw'  # /dev/dma_heap/* (char device 253)"
echo "  - 'c 511:* rmw'  # /dev/vchiq"
echo "  - 'c 81:* rmw'   # /dev/video*"
echo "  - 'c 250:* rmw'  # /dev/media* (media controllers)"
echo ""

generate_docker_compose_override() {
    cat << EOF
version: '3.8'
services:
  motion-in-ocean:
    devices:
EOF
    for device in "${CORE_DEVICES[@]}"; do
        echo "      - $device:$device"
    done
    for device in "${MEDIA_DEVICES[@]}"; do
        echo "      - $device:$device"
    done
    for device in "${VIDEO_DEVICES[@]}"; do
        echo "      - $device:$device"
    done
    cat << EOF
    privileged: true # Required for full device access
EOF
}

# Check camera functionality
echo "🎥 Camera Test:"
echo ""
if command -v rpicam-hello &> /dev/null; then
    echo "Testing camera with rpicam-hello..."
    if timeout 3 rpicam-hello --list-cameras 2>/dev/null; then
        echo "  ✓ Camera detected and working!"
    else
        echo "  ✗ Camera test failed - check camera connection"
    fi
else
    echo "  ⚠️  rpicam-hello not found (install with: sudo apt install libcamera-apps)"
fi

echo ""
echo "✅ Detection complete!"
echo ""
echo "Next steps:"
echo "1. Update docker-compose.yml with the devices shown above"
echo "2. Or use device_cgroup_rules for automatic device access"
echo "3. Run: docker compose up -d"
echo ""
echo -e "Do you want to create a docker-compose.override.yml file with the detected devices? (y/N):"
read -r CREATE_OVERRIDE

if [[ "${CREATE_OVERRIDE}" =~ ^[Yy]$ ]]; then
    generate_docker_compose_override > docker-compose.override.yml
    echo -e "✓ Created docker-compose.override.yml with detected devices."
    echo "You can now run: docker compose -f docker-compose.yml -f docker-compose.override.yml up -d"
else
    echo "Skipping creation of docker-compose.override.yml."
fi
