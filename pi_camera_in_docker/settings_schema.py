"""
Settings Schema Generator
Generates JSON schema for all runtime-editable settings.
Used by /api/settings/schema endpoint to provide UI with metadata.
"""

from typing import Any, ClassVar, Dict, List, Optional, Tuple


class SettingsSchema:
    """
    Generates and provides JSON schema for application settings.
    Includes metadata: property name, type, default, constraints, description, category, etc.
    """

    # Define all editable settings with their schema
    SCHEMA_DEFINITION: ClassVar[Dict[str, Any]] = {
        "camera": {
            "title": "Camera Configuration",
            "description": "Video capture and streaming parameters",
            "properties": {
                "resolution": {
                    "type": "string",
                    "title": "Resolution",
                    "description": 'Video resolution in "WIDTHxHEIGHT" format (e.g., 1280x720)',
                    "default": "640x480",
                    "pattern": r"^\d+x\d+$",
                    "examples": ["640x480", "1280x720", "1920x1080"],
                    "restartable": True,
                    "requires_restart": "Changing resolution requires camera reinit",
                },
                "fps": {
                    "type": "integer",
                    "title": "Frames Per Second",
                    "description": "Capture frame rate (0 = camera default, 1-60 typical range)",
                    "default": 24,
                    "minimum": 0,
                    "maximum": 120,
                    "restartable": True,
                    "requires_restart": "Changing FPS requires camera reinit",
                },
                "jpeg_quality": {
                    "type": "integer",
                    "title": "JPEG Quality",
                    "description": "JPEG compression level (1=lowest quality, fast; 100=highest quality, slow)",
                    "default": 85,
                    "minimum": 1,
                    "maximum": 100,
                    "restartable": False,
                    "requires_restart": None,
                },
                "max_stream_connections": {
                    "type": "integer",
                    "title": "Max Stream Connections",
                    "description": "Maximum number of simultaneous MJPEG stream clients",
                    "default": 2,
                    "minimum": 1,
                    "maximum": 100,
                    "restartable": False,
                    "requires_restart": None,
                },
                "max_frame_age_seconds": {
                    "type": "number",
                    "title": "Frame Cache Age (seconds)",
                    "description": "Maximum age of cached frames before re-encoding (higher = more reuse, stale frames possible)",
                    "default": 10.0,
                    "minimum": 0.5,
                    "maximum": 60.0,
                    "step": 0.5,
                    "restartable": False,
                    "requires_restart": None,
                },
            },
        },
        "feature_flags": {
            "title": "Feature Flags",
            "description": "Experimental and optional features. See docs for details.",
            "properties": {
                # Performance optimization flags
                "QUALITY_ADAPTATION": {
                    "type": "boolean",
                    "title": "Automatic JPEG Quality Adaptation",
                    "description": "Dynamically adjust JPEG quality based on network bandwidth",
                    "default": False,
                    "category": "Performance",
                    "restartable": False,
                    "warning": "May affect image quality in high-latency scenarios",
                },
                "FPS_THROTTLE_ADAPTIVE": {
                    "type": "boolean",
                    "title": "Adaptive FPS Throttling",
                    "description": "Automatically reduce FPS when CPU load exceeds threshold",
                    "default": False,
                    "category": "Performance",
                    "restartable": False,
                },
                "FRAME_SIZE_OPTIMIZATION": {
                    "type": "boolean",
                    "title": "Frame Size Optimization",
                    "description": "Automatically downscale frames for clients with lower resolution capability",
                    "default": True,
                    "category": "Performance",
                    "restartable": False,
                },
                # Experimental features
                "MOTION_DETECTION": {
                    "type": "boolean",
                    "title": "Motion Detection Hooks",
                    "description": "Enable motion detection preprocessing and optional HTTP webhooks",
                    "default": False,
                    "category": "Experimental",
                    "restartable": False,
                    "warning": "Requires external motion detection service",
                },
                "FRAME_RECORDING": {
                    "type": "boolean",
                    "title": "Frame Recording to Disk",
                    "description": "Record streaming frames to local disk for playback/analysis",
                    "default": False,
                    "category": "Experimental",
                    "restartable": False,
                    "warning": "High overhead: generates large videos quickly",
                },
                # Integration & compatibility
                "CORS_SUPPORT": {
                    "type": "boolean",
                    "title": "CORS Support",
                    "description": "Enable Cross-Origin Resource Sharing for browser-based clients",
                    "default": True,
                    "category": "Integration",
                    "restartable": True,
                    "requires_restart": "Changing CORS requires server restart",
                },
                "HOME_ASSISTANT_INTEGRATION": {
                    "type": "boolean",
                    "title": "Home Assistant Integration",
                    "description": "Apply Home Assistant-specific response optimizations",
                    "default": False,
                    "category": "Integration",
                    "restartable": False,
                },
                # Observability
                "PROMETHEUS_METRICS": {
                    "type": "boolean",
                    "title": "Prometheus Metrics Export",
                    "description": "Expose /metrics endpoint with Prometheus-format metrics",
                    "default": False,
                    "category": "Observability",
                    "restartable": False,
                },
                "ENHANCED_FRAME_STATS": {
                    "type": "boolean",
                    "title": "Enhanced Frame Statistics",
                    "description": "Collect detailed per-frame statistics (encode time, size, quality)",
                    "default": False,
                    "category": "Observability",
                    "restartable": False,
                },
                "REQUEST_TRACING": {
                    "type": "boolean",
                    "title": "Request Tracing",
                    "description": "Log complete request lifecycle with timing (extremely verbose)",
                    "default": False,
                    "category": "Observability",
                    "restartable": False,
                    "warning": "Very verbose; impacts readability and performance",
                },
                # Debugging
                "DEBUG_LOGGING": {
                    "type": "boolean",
                    "title": "Enhanced Debug Logging",
                    "description": "Enable DEBUG-level structured logging for development/troubleshooting",
                    "default": False,
                    "category": "Debug",
                    "restartable": False,
                },
                "TRACE_LOGGING": {
                    "type": "boolean",
                    "title": "Trace-Level Logging",
                    "description": "Log at TRACE level: extremely detailed internal state debugging",
                    "default": False,
                    "category": "Debug",
                    "restartable": False,
                    "warning": "Severely impacts performance",
                },
                "PERFORMANCE_PROFILING": {
                    "type": "boolean",
                    "title": "Performance Profiling",
                    "description": "Periodically log CPU, memory, and per-module resource consumption",
                    "default": False,
                    "category": "Debug",
                    "restartable": False,
                },
                "DEVELOPMENT_MODE": {
                    "type": "boolean",
                    "title": "Development Mode",
                    "description": "Relaxes input validation and enables internal debugging endpoints",
                    "default": False,
                    "category": "Debug",
                    "restartable": False,
                    "warning": "SECURITY: Never enable in production",
                },
            },
        },
        "logging": {
            "title": "Logging Configuration",
            "description": "Control logging output verbosity and format",
            "properties": {
                "log_level": {
                    "type": "string",
                    "title": "Log Level",
                    "description": "Logging verbosity level",
                    "default": "INFO",
                    "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                    "restartable": False,
                    "requires_restart": None,
                },
                "log_format": {
                    "type": "string",
                    "title": "Log Format",
                    "description": "Human-readable (text) or structured JSON format",
                    "default": "text",
                    "enum": ["text", "json"],
                    "restartable": True,
                    "requires_restart": "Changing log format requires server restart",
                },
                "log_include_identifiers": {
                    "type": "boolean",
                    "title": "Include Process/Thread IDs",
                    "description": "Include Python process ID and thread ID in log output",
                    "default": False,
                    "restartable": False,
                    "requires_restart": None,
                },
            },
        },
        "discovery": {
            "title": "Node Discovery & Self-Registration",
            "description": "Configure automatic announcement to management node (multi-device setups)",
            "properties": {
                "discovery_enabled": {
                    "type": "boolean",
                    "title": "Enable Discovery",
                    "description": "Announce this webcam to a management node automatically",
                    "default": False,
                    "restartable": False,
                    "requires_restart": None,
                },
                "discovery_management_url": {
                    "type": "string",
                    "title": "Management Node URL",
                    "description": "Base URL where management node is accessible (e.g., http://192.168.1.10:8001)",
                    "default": "http://127.0.0.1:8001",
                    "format": "uri",
                    "restartable": False,
                    "requires_restart": None,
                },
                "discovery_token": {
                    "type": "string",
                    "title": "Discovery Shared Token",
                    "description": "Shared secret (must match NODE_DISCOVERY_SHARED_SECRET on management node)",
                    "default": "",
                    "sensitive": True,
                    "restartable": False,
                    "requires_restart": None,
                },
                "discovery_interval_seconds": {
                    "type": "number",
                    "title": "Discovery Interval (seconds)",
                    "description": "How often to (re)announce to the management node",
                    "default": 30.0,
                    "minimum": 5.0,
                    "maximum": 3600.0,
                    "step": 5.0,
                    "restartable": False,
                    "requires_restart": None,
                },
            },
        },
    }

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """
        Get the complete settings schema.

        Returns:
            Dict with { category: { properties: { ... } } } structure
        """
        return dict(cls.SCHEMA_DEFINITION)

    @classmethod
    def get_category_schema(cls, category: str) -> Optional[Dict[str, Any]]:
        """
        Get schema for a specific category.

        Args:
            category: Category name (camera, feature_flags, logging, discovery)

        Returns:
            Category schema or None if not found
        """
        return cls.SCHEMA_DEFINITION.get(category)

    @classmethod
    def get_property_schema(cls, category: str, property_name: str) -> Optional[Dict[str, Any]]:
        """
        Get schema for a specific property.

        Args:
            category: Category name
            property_name: Property name within category

        Returns:
            Property schema or None if not found
        """
        category_schema = cls.SCHEMA_DEFINITION.get(category, {})
        properties = category_schema.get("properties", {})
        return properties.get(property_name)

    @staticmethod
    def _validate_boolean(value: Any, _schema: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate boolean value.

        Args:
            value: Value to validate
            _schema: Property schema (unused for boolean)

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(value, bool):
            return False, f"Expected boolean, got {type(value).__name__}"
        return True, None

    @staticmethod
    def _validate_integer(value: Any, schema: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate integer value with min/max constraints.

        Args:
            value: Value to validate
            schema: Property schema with optional 'minimum' and 'maximum'

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(value, int) or isinstance(value, bool):
            return False, f"Expected integer, got {type(value).__name__}"
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if minimum is not None and value < minimum:
            return False, f"Value {value} is less than minimum {minimum}"
        if maximum is not None and value > maximum:
            return False, f"Value {value} is greater than maximum {maximum}"
        return True, None

    @staticmethod
    def _validate_number(value: Any, schema: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate number (int/float) value with constraints.

        Args:
            value: Value to validate
            schema: Property schema with optional 'minimum' and 'maximum'

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return False, f"Expected number, got {type(value).__name__}"
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if minimum is not None and value < minimum:
            return False, f"Value {value} is less than minimum {minimum}"
        if maximum is not None and value > maximum:
            return False, f"Value {value} is greater than maximum {maximum}"
        return True, None

    @staticmethod
    def _validate_string(value: Any, schema: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate string value with optional enum constraint.

        Args:
            value: Value to validate
            schema: Property schema with optional 'enum' list

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(value, str):
            return False, f"Expected string, got {type(value).__name__}"
        enum = schema.get("enum")
        if enum and value not in enum:
            return False, f"Value must be one of: {', '.join(enum)}"
        return True, None

    @classmethod
    def validate_value(
        cls, category: str, property_name: str, value: Any
    ) -> Tuple[bool, Optional[str]]:
        """Validate a value against schema constraints.

        Dispatches to type-specific validators based on schema type.

        Args:
            category: Category name
            property_name: Property name
            value: Value to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        prop_schema = cls.get_property_schema(category, property_name)
        if not prop_schema:
            return False, f"Unknown property: {category}.{property_name}"

        prop_type = prop_schema.get("type")
        validators = {
            "boolean": cls._validate_boolean,
            "integer": cls._validate_integer,
            "number": cls._validate_number,
            "string": cls._validate_string,
        }

        validator = validators.get(prop_type)
        if validator:
            return validator(value, prop_schema)

        return True, None

    @classmethod
    def get_defaults(cls) -> Dict[str, Dict[str, Any]]:
        """
        Extract default values for all settings.

        Returns:
            Dict with { category: { property: default_value } } structure
        """
        defaults: Dict[str, Dict[str, Any]] = {}
        for category, schema in cls.SCHEMA_DEFINITION.items():
            defaults[category] = {}
            for prop_name, prop_schema in schema.get("properties", {}).items():
                if "default" in prop_schema:
                    defaults[category][prop_name] = prop_schema["default"]
        return defaults

    @classmethod
    def get_restartable_properties(cls) -> Dict[str, List[str]]:
        """
        Get list of properties that require restart when changed.

        Returns:
            Dict with { category: [property_names] } structure
        """
        restartable: Dict[str, List[str]] = {}
        for category, schema in cls.SCHEMA_DEFINITION.items():
            restartable[category] = []
            for prop_name, prop_schema in schema.get("properties", {}).items():
                if prop_schema.get("restartable", False):
                    restartable[category].append(prop_name)
        return restartable
