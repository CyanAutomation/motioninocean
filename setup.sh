#!/bin/bash
set -e

ENV_FILE=".env"
ENV_EXAMPLE=".env.example"
OVERRIDE_FILE="docker-compose.override.yaml"

copy_env() {
    if [ -f "$ENV_FILE" ]; then
        echo "[INFO] $ENV_FILE already exists."
        return
    fi

    if [ -f "$ENV_EXAMPLE" ]; then
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        echo "[INFO] Copied $ENV_EXAMPLE to $ENV_FILE."
        echo "   Review and update $ENV_FILE as needed."
    else
        echo "[WARN] $ENV_EXAMPLE not found. Please create $ENV_FILE manually."
    fi
}

run_device_detection() {
    echo ""
    echo "Would you like to run ./detect-devices.sh to generate device mappings? (y/N):"
    read -r RUN_DETECT

    if [[ "$RUN_DETECT" =~ ^[Yy]$ ]]; then
        if [ -x "./detect-devices.sh" ]; then
            ./detect-devices.sh
        else
            echo "[WARN] ./detect-devices.sh not found or not executable. Skipping device detection."
        fi
    else
        echo "Skipping device detection."
    fi
}

choose_profile() {
    local profile_input

    echo ""
    echo "Select which profile(s) to start:"
    echo "  1) webcam"
    echo "  2) management"
    echo "  3) both (webcam + management)"
    echo "Enter choice [1-3] (default: 1):"
    read -r profile_input

    case "$profile_input" in
        ""|1)
            COMPOSE_PROFILE_ARGS="--profile webcam"
            ;;
        2)
            COMPOSE_PROFILE_ARGS="--profile management"
            ;;
        3)
            COMPOSE_PROFILE_ARGS="--profile webcam --profile management"
            ;;
        *)
            echo "[WARN] Invalid choice '$profile_input'. Defaulting to webcam profile."
            COMPOSE_PROFILE_ARGS="--profile webcam"
            ;;
    esac
}

print_compose_command() {
    echo ""
    echo "[WARN] Running 'docker compose up -d' without --profile will not start profile-gated services."
    echo "Next, run:"

    if [ -f "$OVERRIDE_FILE" ]; then
        echo "docker compose -f docker-compose.yaml -f docker-compose.override.yaml $COMPOSE_PROFILE_ARGS up -d"
    else
        echo "docker compose $COMPOSE_PROFILE_ARGS up -d"
    fi
}

copy_env
run_device_detection
choose_profile
print_compose_command
