#!/bin/bash
# Motion In Ocean - Interactive Setup Assistant
# Supports both new directory-based deployments and legacy root-level setup
#
# NEW RECOMMENDED APPROACH:
#   cd containers/motioniocean-{webcam|management}
#   /path/to/setup.sh
#
# LEGACY APPROACH (deprecated):
#   /path/to/setup.sh  (from repo root)

set -e

# Determine if running from repo root or a container directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CURRENT_DIR="$(pwd)"

# Detect if we're in a container subdirectory
CONTAINER_MODE=false
DEPLOYMENT_MODE=""

if [ -d "$CURRENT_DIR/../../containers/motioniocean-webcam" ] 2>/dev/null || \
   [[ "$CURRENT_DIR" == *"motioniocean-webcam"* ]]; then
    CONTAINER_MODE=true
    DEPLOYMENT_MODE="webcam"
elif [ -d "$CURRENT_DIR/../../containers/motioniocean-management" ] 2>/dev/null || \
     [[ "$CURRENT_DIR" == *"motioniocean-management"* ]]; then
    CONTAINER_MODE=true
    DEPLOYMENT_MODE="management"
fi

# Paths for environment files
ENV_FILE=".env"
ENV_EXAMPLE=".env.example"
# shellcheck disable=SC2034  # Variable is a constant for generated file name
OVERRIDE_FILE="docker-compose.override.yaml"

copy_env() {
    if [ -f "$ENV_FILE" ]; then
        echo "[INFO] $ENV_FILE already exists."
        return
    fi

    if [ -f "$ENV_EXAMPLE" ]; then
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        echo "[INFO] Copied $ENV_EXAMPLE to $ENV_FILE."
        echo "       Review and update $ENV_FILE as needed."
    else
        echo "[WARN] $ENV_EXAMPLE not found. Please create $ENV_FILE manually."
    fi
}

run_device_detection() {
    # Only offer device detection for webcam mode
    if [ "$DEPLOYMENT_MODE" != "webcam" ]; then
        return
    fi

    echo ""
    echo "Webcam mode detected. Would you like to run device detection?"
    echo "This generates docker-compose.override.yaml with your system's camera devices. (y/N):"
    read -r RUN_DETECT

    if [[ "$RUN_DETECT" =~ ^[Yy]$ ]]; then
        DETECT_SCRIPT="$SCRIPT_DIR/detect-devices.sh"
        if [ -x "$DETECT_SCRIPT" ]; then
            "$DETECT_SCRIPT" "$CURRENT_DIR"
        else
            echo "[WARN] detect-devices.sh not found or not executable. Skipping device detection."
        fi
    else
        echo "Skipping device detection."
    fi
}

print_next_steps() {
    echo ""
    echo "=========================================="
    echo "Setup Complete!"
    echo "=========================================="
    echo ""

    if [ "$CONTAINER_MODE" = true ]; then
        echo "Mode: $DEPLOYMENT_MODE (directory-based deployment)"
        echo ""
        echo "Next, start the service:"
        echo "  docker compose up -d"
        echo ""
        echo "View logs:"
        echo "  docker compose logs -f"
        echo ""
        echo "Check health:"
        echo "  curl http://localhost:${MOTION_IN_OCEAN_PORT:-8000}/health"
    else
        echo "Mode: Legacy root-level deployment (deprecated)"
        echo "    Consider migrating to containers/motioniocean-{mode}/"
        echo "    See MIGRATION.md for guidance."
        echo ""
        echo "Next, select a deployment mode:"
        choose_profiles_legacy
    fi
}

choose_profiles_legacy() {
    echo ""
    echo "Select deployment mode:"
    echo "  1) webcam (camera streaming)"
    echo "  2) management (node coordination hub)"
    echo "  3) both (webcam + management)"
    echo "Enter choice [1-3] (default: 1):"
    read -r profile_input

    case "$profile_input" in
        ""|1)
            MODE="webcam"
            ;;
        2)
            MODE="management"
            ;;
        3)
            MODE="both"
            ;;
        *)
            echo "[WARN] Invalid choice. Defaulting to webcam."
            MODE="webcam"
            ;;
    esac

    echo ""
    echo "To start using legacy files, run:"
    case "$MODE" in
        webcam)
            echo "  docker compose -f docker-compose.webcam.yaml up -d"
            ;;
        management)
            echo "  docker compose -f docker-compose.management.yaml up -d"
            ;;
        both)
            echo "  docker compose -f docker-compose.webcam.yaml up -d"
            echo "  docker compose -f docker-compose.management.yaml up -d"
            ;;
    esac
    echo ""
    echo "⚠️ DEPRECATION NOTICE:"
    echo "   Custom-named compose files are deprecated."
    echo "   Migrate to: containers/motioniocean-{mode}/"
    echo "   See MIGRATION.md for details."
}

# Main execution
echo "=========================================="
echo "Motion In Ocean - Setup Assistant"
echo "=========================================="
echo ""

if [ "$CONTAINER_MODE" = true ]; then
    echo "Detected directory mode: $DEPLOYMENT_MODE"
else
    echo "Detected: Repository root (legacy mode)"
fi

echo ""

copy_env
run_device_detection
print_next_steps
