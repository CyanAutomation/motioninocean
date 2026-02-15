"""
Settings Management API Endpoints
Provides runtime configuration management via REST API.
Endpoints: GET /api/settings, PATCH /api/settings, POST /api/settings/reset, GET /api/settings/schema
"""

from typing import Any, Dict, Tuple

from config_validator import validate_settings_patch
from flask import Flask, current_app, jsonify, request
from settings_schema import SettingsSchema


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
            settings = current_app.application_settings.load()
            merged = {
                "source": "merged",  # env + persisted
                "settings": settings.get("settings", {}),
                "last_modified": settings.get("last_modified"),
                "modified_by": settings.get("modified_by"),
            }
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
            
            return jsonify({
                "schema": schema,
                "defaults": defaults,
                "restartable_properties": restartable,
            }), 200
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
            patch_data = request.get_json()
            if not patch_data:
                return jsonify({"error": "Empty request body"}), 400

            # Validate patch
            validation_errors = validate_settings_patch(patch_data)
            if validation_errors:
                return jsonify({
                    "error": "Validation failed",
                    "validation_errors": validation_errors,
                }), 400

            # Check which properties require restart
            restartable_properties = SettingsSchema.get_restartable_properties()
            modified_on_restart = []
            effective_patch = {}

            for category, properties in patch_data.items():
                effective_patch[category] = {}
                for prop_name, value in properties.items():
                    if prop_name in restartable_properties.get(category, []):
                        modified_on_restart.append(f"{category}.{prop_name}")
                        # Still save it; mark as pending restart
                    effective_patch[category][prop_name] = value

            # Load current settings and apply patch
            current = current_app.application_settings.load()
            current_settings = current.get("settings", {})

            for category, properties in effective_patch.items():
                if category not in current_settings:
                    current_settings[category] = {}
                current_settings[category].update(properties)

            # Persist changes
            current_app.application_settings.save(
                current_settings,
                modified_by="api_patch"
            )

            # Return result
            result = {
                "saved": True,
                "settings": current_settings,
                "last_modified": current.get("last_modified"),
                "modified_by": "api_patch",
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
            return jsonify({
                "reset": True,
                "message": "Settings reset to defaults. Environment variables are now source of truth."
            }), 200
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
            # Collect environment defaults
            import os
            from main import _parse_resolution
            
            env_defaults = {
                "camera": {
                    "resolution": _parse_resolution(os.environ.get("RESOLUTION", "640x480")).replace(',', 'x'),
                    "fps": int(os.environ.get("FPS", "0")),
                    "jpeg_quality": int(os.environ.get("JPEG_QUALITY", "85")),
                    "max_stream_connections": int(os.environ.get("MAX_STREAM_CONNECTIONS", "2")),
                    "max_frame_age_seconds": float(os.environ.get("MAX_FRAME_AGE_SECONDS", "10")),
                },
                "logging": {
                    "log_level": os.environ.get("LOG_LEVEL", "INFO"),
                    "log_format": os.environ.get("LOG_FORMAT", "text"),
                    "log_include_identifiers": os.environ.get("LOG_INCLUDE_IDENTIFIERS", "false").lower() in ("1", "true", "yes"),
                },
                "discovery": {
                    "discovery_enabled": os.environ.get("DISCOVERY_ENABLED", "false").lower() in ("1", "true", "yes"),
                    "discovery_management_url": os.environ.get("DISCOVERY_MANAGEMENT_URL", "http://127.0.0.1:8001"),
                    "discovery_token": os.environ.get("DISCOVERY_TOKEN", ""),
                    "discovery_interval_seconds": float(os.environ.get("DISCOVERY_INTERVAL_SECONDS", "30")),
                },
                "feature_flags": {},  # Would need to iterate through all flags
            }
            
            changes = current_app.application_settings.get_changes_from_env(env_defaults)
            return jsonify(changes), 200
        except Exception as exc:
            return (
                jsonify({"error": "Failed to get settings changes", "details": str(exc)}),
                500,
            )
