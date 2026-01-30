#!/bin/bash
set -e

ENV_FILE=".env"
ENV_EXAMPLE=".env.example"
OVERRIDE_FILE="docker-compose.override.yaml"

copy_env() {
    if [ -f "$ENV_FILE" ]; then
        echo "✅ $ENV_FILE already exists."
        return
    fi

    if [ -f "$ENV_EXAMPLE" ]; then
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        echo "✅ Copied $ENV_EXAMPLE to $ENV_FILE."
        echo "   Review and update $ENV_FILE as needed."
    else
        echo "⚠️  $ENV_EXAMPLE not found. Please create $ENV_FILE manually."
    fi
}

run_device_detection() {
    echo ""
    echo "Would you like to run ./detect-devices.sh to generate device mappings? (y/N):"
    read -r RUN_DETECT

    if [[ "$RUN_DETECT" =~ ^[Yy]$ ]]; then
        ./detect-devices.sh
    else
        echo "Skipping device detection."
    fi
}

print_compose_command() {
    echo ""
    if [ -f "$OVERRIDE_FILE" ]; then
        echo "Next, run:"
        echo "docker compose -f docker-compose.yaml -f docker-compose.override.yaml up -d"
    else
        echo "Next, run:"
        echo "docker compose up -d"
    fi
}

copy_env
run_device_detection
print_compose_command
