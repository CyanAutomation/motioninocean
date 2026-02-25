"""
Settings Management API Endpoints
Provides runtime configuration management via REST API.
Endpoints: GET /api/settings, PATCH /api/settings, POST /api/settings/reset, GET /api/settings/schema
"""

import functools
import hashlib
import json as _json
import os
from typing import Any, Dict, Tuple

import sentry_sdk
from flask import Blueprint, Flask, Response, current_app, jsonify, redirect, request

from .config_validator import validate_settings_patch
from .runtime_config import (
    _load_camera_config,
    get_effective_settings_payload,
    parse_resolution,
)
from .settings_schema import SettingsSchema


# Module-level ETag cache for the settings schema.
# The schema is immutable at runtime so it is hashed once and reused.


@functools.lru_cache(maxsize=1)
def _get_schema_etag() -> str:
    """Compute and cache a stable ETag for the settings schema.

    Hashes the schema JSON once per process lifetime using lru_cache.

    Returns:
        MD5 hex digest suitable for use as an HTTP ETag value.
    """
    schema = SettingsSchema.get_schema()
    return hashlib.md5(
        _json.dumps(schema, sort_keys=True).encode()
    ).hexdigest()


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
        width, height = parse_resolution(os.environ.get("MIO_RESOLUTION", "640x480"))
        resolution = f"{width}x{height}"
    except ValueError:
        resolution = f"{camera_env_config['resolution'][0]}x{camera_env_config['resolution'][1]}"

    return {
        "camera": {
            "resolution": resolution,
            "fps": _safe_int_env("MIO_FPS", camera_env_config["fps"]),
            "jpeg_quality": _safe_int_env("MIO_JPEG_QUALITY", camera_env_config["jpeg_quality"]),
            "max_stream_connections": _safe_int_env(
                "MIO_MAX_STREAM_CONNECTIONS", camera_env_config["max_stream_connections"]
            ),
            "max_frame_age_seconds": _safe_float_env(
                "MIO_MAX_FRAME_AGE_SECONDS", camera_env_config["max_frame_age_seconds"]
            ),
        },
        "logging": {
            "log_level": os.environ.get("MIO_LOG_LEVEL", "INFO"),
            "log_format": os.environ.get("MIO_LOG_FORMAT", "text"),
            "log_include_identifiers": os.environ.get(
                "MIO_LOG_INCLUDE_IDENTIFIERS", "false"
            ).lower()
            in ("1", "true", "yes"),
        },
        "discovery": {
            "discovery_enabled": os.environ.get("MIO_DISCOVERY_ENABLED", "false").lower()
            in ("1", "true", "yes"),
            "discovery_management_url": os.environ.get(
                "MIO_DISCOVERY_MANAGEMENT_URL", "http://127.0.0.1:8001"
            ),
            "discovery_token": os.environ.get("MIO_DISCOVERY_TOKEN", ""),
            "discovery_interval_seconds": _safe_float_env("MIO_DISCOVERY_INTERVAL_SECONDS", 30),
        },
        "feature_flags": {},  # Would need to iterate through all flags
    }


def _register_settings_deprecated_v0_aliases(app: Flask) -> None:
    """Register legacy /api/settings* routes that redirect (HTTP 308) to /api/v1/settings* equivalents.

    These aliases exist for backward compatibility. All routes return HTTP 308 Permanent
    Redirect with a ``Deprecation: true`` header. HTTP 308 preserves the request method
    and body on redirect.

    Args:
        app: Flask application instance to register the deprecated routes on.
    """

    def _deprecated_redirect(new_path: str):
        resp = redirect(new_path, 308)
        resp.headers["Deprecation"] = "true"
        resp.headers["Link"] = f'<{new_path}>; rel="successor-version"'
        return resp

    @app.route("/api/settings", methods=["GET", "PATCH"])
    def deprecated_settings():
        return _deprecated_redirect("/api/v1/settings")

    @app.route("/api/settings/schema", methods=["GET"])
    def deprecated_settings_schema():
        return _deprecated_redirect("/api/v1/settings/schema")

    @app.route("/api/settings/reset", methods=["POST"])
    def deprecated_settings_reset():
        return _deprecated_redirect("/api/v1/settings/reset")

    @app.route("/api/settings/changes", methods=["GET"])
    def deprecated_settings_changes():
        return _deprecated_redirect("/api/v1/settings/changes")


def create_settings_blueprint() -> Blueprint:
    """Create a Flask Blueprint containing all settings API routes at /settings/*.

    Callers should register it on a Flask app with ``url_prefix="/api/v1"``.

    Returns:
        Flask Blueprint with all settings routes registered.
    """
    bp = Blueprint("settings_api", __name__)

    @bp.route("/settings", methods=["GET"])
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
            sentry_sdk.capture_exception(exc)
            return (
                jsonify({"error": "Failed to load settings", "details": str(exc)}),
                500,
            )

    @bp.route("/settings/schema", methods=["GET"])
    def get_settings_schema() -> Any:
        """
        Get JSON schema for all editable settings.
        Describes: property names, types, defaults, constraints, descriptions, categories.

        Returns:
            JSON schema with metadata for UI rendering; cached via ETag.
        """
        try:
            etag = _get_schema_etag()
            client_etag = request.headers.get("If-None-Match", "")
            if client_etag == etag:
                return Response(status=304)

            schema = SettingsSchema.get_schema()
            defaults = SettingsSchema.get_defaults()
            restartable = SettingsSchema.get_restartable_properties()

            resp = jsonify(
                {
                    "schema": schema,
                    "defaults": defaults,
                    "restartable_properties": restartable,
                }
            )
            resp.headers["ETag"] = etag
            resp.headers["Cache-Control"] = "public, max-age=3600"
        except Exception as exc:
            sentry_sdk.capture_exception(exc)
            return (
                jsonify({"error": "Failed to generate settings schema", "details": str(exc)}),
                500,
            )
        else:
            return resp, 200

    @bp.route("/settings", methods=["PATCH"])
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
            sentry_sdk.capture_exception(exc)
            return (
                jsonify({"error": "Failed to update settings", "details": str(exc)}),
                500,
            )

    @bp.route("/settings/reset", methods=["POST"])
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
            sentry_sdk.capture_exception(exc)
            return (
                jsonify({"error": "Failed to reset settings", "details": str(exc)}),
                500,
            )

    @bp.route("/settings/changes", methods=["GET"])
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
            sentry_sdk.capture_exception(exc)
            return (
                jsonify({"error": "Failed to get settings changes", "details": str(exc)}),
                500,
            )

    return bp


def register_settings_routes(app: Flask) -> None:
    """Register all settings management API routes.

    Registers versioned routes under ``/api/v1/settings*`` via a Flask Blueprint, plus
    deprecated ``/api/settings*`` aliases that return HTTP 308 redirects. New clients
    should target ``/api/v1/settings*`` directly.

    Routes (versioned):
    - GET  /api/v1/settings         — Current runtime settings (merged env + persisted)
    - GET  /api/v1/settings/schema  — JSON schema describing all editable settings
    - PATCH /api/v1/settings        — Validate and persist setting changes
    - POST /api/v1/settings/reset   — Clear persisted settings, revert to env defaults
    - GET  /api/v1/settings/changes — Diff between env defaults and persisted overrides

    Args:
        app: Flask application instance.
    """
    bp = create_settings_blueprint()
    app.register_blueprint(bp, url_prefix="/api/v1")
    _register_settings_deprecated_v0_aliases(app)
