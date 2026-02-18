"""
Settings Management API Endpoints
Provides runtime configuration management via REST API.
Endpoints: GET /api/settings, PATCH /api/settings, POST /api/settings/reset, GET /api/settings/schema
"""

import os
from typing import Any, Dict, Tuple

from flask import Flask, current_app, jsonify, request

from .config_validator import validate_settings_patch
from .runtime_config import (
    _load_camera_config,
    get_effective_settings_payload,
    parse_resolution,
)
from .settings_schema import SettingsSchema


def _safe_int_env(name: str, default: int) -> int:
    """Load integer from environment variable with fallback.

    Args:
        name: Environment variable name.
        default: Default value if not set or invalid.

    Returns:
        Integer value from env or default.
    """
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float_env(name: str, default: float) -> float:
    """Load float from environment variable with fallback.

    Args:
        name: Environment variable name.
        default: Default value if not set or invalid.

    Returns:
        Float value from env or default.
    """
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _load_env_settings_defaults() -> Dict[str, Dict[str, Any]]:
    """Load settings defaults from environment variables.

    Returns:
        Dict with structure { category: { property: value } }.
    """
    camera_env_config = _load_camera_config()
    try:
        width, height = parse_resolution(os.environ.get("RESOLUTION", "640x480"))
        resolution = f"{width}x{height}"
    except ValueError:
        resolution = f"{camera_env_config['resolution'][0]}x{camera_env_config['resolution'][1]}"

    return {
        "camera": {
            "resolution": resolution,
            "fps": _safe_int_env("FPS", camera_env_config["fps"]),
            "jpeg_quality": _safe_int_env("JPEG_QUALITY", camera_env_config["jpeg_quality"]),
            "max_stream_connections": _safe_int_env(
                "MAX_STREAM_CONNECTIONS", camera_env_config["max_stream_connections"]
            ),
            "max_frame_age_seconds": _safe_float_env(
                "MAX_FRAME_AGE_SECONDS", camera_env_config["max_frame_age_seconds"]
            ),
        },
        "logging": {
            "log_level": os.environ.get("LOG_LEVEL", "INFO"),
            "log_format": os.environ.get("LOG_FORMAT", "text"),
            "log_include_identifiers": os.environ.get("LOG_INCLUDE_IDENTIFIERS", "false").lower()
            in ("1", "true", "yes"),
        },
        "discovery": {
            "discovery_enabled": os.environ.get("DISCOVERY_ENABLED", "false").lower()
            in ("1", "true", "yes"),
            "discovery_management_url": os.environ.get(
                "DISCOVERY_MANAGEMENT_URL", "http://127.0.0.1:8001"
            ),
            "discovery_token": os.environ.get("DISCOVERY_TOKEN", ""),
            "discovery_interval_seconds": _safe_float_env("DISCOVERY_INTERVAL_SECONDS", 30),
        },
        "feature_flags": {},  # Would need to iterate through all flags
    }


def register_settings_routes(app: Flask) -> None:
    """
    Register all settings management API routes.

    Routes:
    - GET /api/settings — Current runtime settings (merged env + persisted)
    - GET /api/settings/schema — JSON schema describing all editable settings
    - PATCH /api/settings — Validate and persist setting changes
    - POST /api/settings/reset — Clear persisted settings, revert to env defaults
    - GET /api/settings/changes — Diff between env defaults and persisted overrides
    """

    @app.route("/api/settings", methods=["GET"])
    def get_settings() -> Tuple[Dict[str, Any], int]:
        """
        Get current runtime settings (merged environment + persisted).

        Returns:
            JSON with current settings merged from env and persisted storage
        """
        try:
            merged = get_effective_settings_payload(current_app.application_settings)
            return jsonify(merged), 200
        except Exception as exc:
            return (
                jsonify({"error": "Failed to load settings", "details": str(exc)}),
                500,
            )

    @app.route("/api/settings/schema", methods=["GET"])
    def get_settings_schema() -> Tuple[Dict[str, Any], int]:
        """
        Get JSON schema for all editable settings.
        Describes: property names, types, defaults, constraints, descriptions, categories.

        Returns:
            JSON schema with metadata for UI rendering
        """
        try:
            schema = SettingsSchema.get_schema()
            defaults = SettingsSchema.get_defaults()
            restartable = SettingsSchema.get_restartable_properties()

            return jsonify(
                {
                    "schema": schema,
                    "defaults": defaults,
                    "restartable_properties": restartable,
                }
            ), 200
        except Exception as exc:
            return (
                jsonify({"error": "Failed to generate settings schema", "details": str(exc)}),
                500,
            )

    @app.route("/api/settings", methods=["PATCH"])
    def patch_settings() -> Tuple[Dict[str, Any], int]:
        """
        Update runtime settings.

        Request body: JSON with structure { category: { property: value } }
        Example:
            {
              "camera": {
                "fps": 60,
                "jpeg_quality": 80
              },
              "logging": {
                "log_level": "DEBUG"
              }
            }

        Returns:
            - 200: Settings updated successfully; merged current settings
            - 400: Validation error (includes per-property error messages)
            - 422: Settings contain properties requiring restart (includes modified_on_restart list)
            - 500: Server error
        """
        try:
            patch_data = request.get_json(silent=True)

            if patch_data is None:
                return (
                    jsonify(
                        {
                            "error": "INVALID_JSON",
                            "message": "Request body must be valid JSON.",
                        }
                    ),
                    400,
                )

            if not isinstance(patch_data, dict):
                return (
                    jsonify(
                        {
                            "error": "INVALID_PAYLOAD",
                            "message": "Request body must be a JSON object.",
                        }
                    ),
                    400,
                )

            if not patch_data:
                return (
                    jsonify(
                        {
                            "error": "INVALID_PAYLOAD",
                            "message": "Request body must not be empty.",
                        }
                    ),
                    400,
                )

            # Validate patch
            validation_errors = validate_settings_patch(patch_data)
            if validation_errors:
                return jsonify(
                    {
                        "error": "Validation failed",
                        "validation_errors": validation_errors,
                    }
                ), 400

            # Check which properties require restart
            restartable_properties = SettingsSchema.get_restartable_properties()
            modified_on_restart = []
            effective_patch: Dict[str, Dict[str, Any]] = {}

            for category, properties in patch_data.items():
                effective_patch[category] = {}
                for prop_name, value in properties.items():
                    if prop_name in restartable_properties.get(category, []):
                        modified_on_restart.append(f"{category}.{prop_name}")
                        # Still save it; mark as pending restart
                    effective_patch[category][prop_name] = value

            # Persist changes in one lock-protected read-modify-write cycle
            persisted = current_app.application_settings.apply_patch_atomic(
                effective_patch,
                modified_by="api_patch",
            )

            # Return result
            result = {
                "saved": True,
                "settings": persisted.get("settings", {}),
                "last_modified": persisted.get("last_modified"),
                "modified_by": persisted.get("modified_by"),
            }

            if modified_on_restart:
                result["modified_on_restart"] = modified_on_restart
                result["requires_restart"] = True
                return jsonify(result), 422  # 422 Unprocessable Entity - saved but restart needed

            return jsonify(result), 200

        except Exception as exc:
            return (
                jsonify({"error": "Failed to update settings", "details": str(exc)}),
                500,
            )

    @app.route("/api/settings/reset", methods=["POST"])
    def reset_settings() -> Tuple[Dict[str, Any], int]:
        """
        Reset persisted settings to defaults (clear JSON file).
        Next restart will use environment variables as sole source.

        Returns:
            - 200: Settings reset successfully
            - 500: Server error
        """
        try:
            current_app.application_settings.reset(modified_by="api_reset")
            return jsonify(
                {
                    "reset": True,
                    "message": "Settings reset to defaults. Environment variables are now source of truth.",
                }
            ), 200
        except Exception as exc:
            return (
                jsonify({"error": "Failed to reset settings", "details": str(exc)}),
                500,
            )

    @app.route("/api/settings/changes", methods=["GET"])
    def get_settings_changes() -> Tuple[Dict[str, Any], int]:
        """
        Get diff between environment defaults and persisted overrides.
        Shows which settings have been changed via UI.

        Returns:
            JSON with 'overridden' list of { category, key, value, env_value } objects
        """
        try:
            env_defaults = _load_env_settings_defaults()
            changes = current_app.application_settings.get_changes_from_env(env_defaults)
            return jsonify(changes), 200
        except Exception as exc:
            return (
                jsonify({"error": "Failed to get settings changes", "details": str(exc)}),
                500,
            )
