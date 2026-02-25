# Environment Variables (Runtime-Implemented)

This document lists environment variables that are **currently read by runtime code** in:

- `pi_camera_in_docker/runtime_config.py`
- `pi_camera_in_docker/feature_flags.py`
- `pi_camera_in_docker/management_api.py`

Anything not in the implemented sections below should be treated as **not runtime-supported**.

## Implemented runtime configuration toggles

These variables configure runtime behavior but are **not** feature flags.

### Application mode and networking

- `MIO_APP_MODE` (default: `webcam`) — valid values: `webcam`, `management`.
- `MIO_BIND_HOST` (default: `127.0.0.1`).
- `MIO_PORT` (default: `8000`).
- `MIO_BASE_URL` (default: `http://<hostname>:8000`).
- `MIO_CORS_ORIGINS` (default: empty/disabled).
- `MIO_CORS_SUPPORT` (deprecated compatibility alias used only if `MIO_CORS_ORIGINS` is unset).

### Camera and stream tuning

- `MIO_RESOLUTION` (default: `640x480`).
- `MIO_FPS` (default: `24`).
- `MIO_TARGET_FPS` (default: same as `MIO_FPS`).
- `MIO_JPEG_QUALITY` (default: `90`).
- `MIO_MAX_FRAME_AGE_SECONDS` (default: `10`).
- `MIO_MAX_STREAM_CONNECTIONS` (default: `10`).

### Discovery and management integration

- `MIO_DISCOVERY_ENABLED` (default: `false`).
- `MIO_DISCOVERY_MANAGEMENT_URL` (default: `http://127.0.0.1:8001`).
- `MIO_DISCOVERY_TOKEN` (default: empty).
- `MIO_DISCOVERY_INTERVAL_SECONDS` (default: `30`).
- `MIO_DISCOVERY_WEBCAM_ID` (default: empty).
- `MIO_NODE_DISCOVERY_SHARED_SECRET` (default: empty; read by management discovery endpoint auth).
- `MIO_NODE_REGISTRY_PATH` (default: `/data/node-registry.json`).

### Logging and diagnostics

- `MIO_LOG_LEVEL` (default: `INFO`).
- `MIO_LOG_FORMAT` (default: `text`).
- `MIO_LOG_INCLUDE_IDENTIFIERS` (default: `false`).

### Auth, startup, and advanced runtime behavior

- `MIO_APPLICATION_SETTINGS_PATH` (default: `/data/application-settings.json`).
- `MIO_MANAGEMENT_AUTH_TOKEN` (default: empty).
- `MIO_WEBCAM_CONTROL_PLANE_AUTH_TOKEN` (default: empty).
- `MIO_FAIL_ON_CAMERA_INIT_ERROR` (default: `false`).
- `MIO_PI3_PROFILE` (default: `false`).
- `MIO_API_TEST_MODE_ENABLED` (default: `false`).
- `MIO_API_TEST_CYCLE_INTERVAL_SECONDS` (default: `5`).
- `MIO_ALLOW_PRIVATE_IPS` (default: `false`; management SSRF private-IP override).

## Implemented feature flags

Only variables registered in `feature_flags.py` and consumed through `is_flag_enabled(...)` are feature flags.

- `MIO_MOCK_CAMERA` (flag: `MOCK_CAMERA`, default: `false`).

## Roadmap / non-implemented / historical variables

> ⚠️ **Non-support notice:** The variables below are **not currently read by runtime code** in the three runtime sources listed at the top of this document. Setting them has no effect unless future implementation explicitly adds runtime reads.

### Previously documented but not currently runtime-implemented

- `MOTION_IN_OCEAN_IMAGE_TAG`
- `MOTION_IN_OCEAN_PORT`
- `MOTION_IN_OCEAN_BIND_HOST`
- `TZ`
- `APP_MODE`
- `MOTION_IN_OCEAN_RESOLUTION`
- `MOTION_IN_OCEAN_FPS`
- `MOTION_IN_OCEAN_TARGET_FPS`
- `MOTION_IN_OCEAN_JPEG_QUALITY`
- `MOTION_IN_OCEAN_MAX_STREAM_CONNECTIONS`
- `MANAGEMENT_AUTH_TOKEN`
- `NODE_DISCOVERY_SHARED_SECRET`
- `DISCOVERY_ENABLED`
- `DISCOVERY_MANAGEMENT_URL`
- `DISCOVERY_TOKEN`
- `DISCOVERY_INTERVAL_SECONDS`
- `DISCOVERY_WEBCAM_ID`
- `BASE_URL`
- `LOG_LEVEL`
- `LOG_FORMAT`
- `LOG_INCLUDE_IDENTIFIERS`
- `MAX_FRAME_AGE_SECONDS`
- `API_TEST_MODE_ENABLED`
- `API_TEST_CYCLE_INTERVAL_SECONDS`
- `LIMITER_STORAGE_URI`
- `NODE_REGISTRY_PATH`
- `MOTION_IN_OCEAN_CAMERA_INIT_REQUIRED`
- `DOCKER_PROXY_PORT`
- `PI3_PROFILE`
- `MOCK_CAMERA`
- `MOTION_IN_OCEAN_ALLOW_PRIVATE_IPS`

### Historical/experimental names that are not runtime-implemented feature flags

- `MOTION_IN_OCEAN_QUALITY_ADAPTATION`
- `MOTION_IN_OCEAN_FPS_THROTTLE_ADAPTIVE`
- `MOTION_IN_OCEAN_FRAME_SIZE_OPTIMIZATION`
- `MOTION_IN_OCEAN_PI3_OPTIMIZATION`
- `MOTION_IN_OCEAN_PI5_OPTIMIZATION`
- `MOTION_IN_OCEAN_MULTI_CAMERA_SUPPORT`
- `MOTION_IN_OCEAN_DEBUG_LOGGING`
- `MOTION_IN_OCEAN_TRACE_LOGGING`
- `MOTION_IN_OCEAN_PERFORMANCE_PROFILING`
- `MOTION_IN_OCEAN_DEVELOPMENT_MODE`
- `MOTION_IN_OCEAN_MOTION_DETECTION`
- `MOTION_IN_OCEAN_FRAME_RECORDING`
- `MOTION_IN_OCEAN_HOME_ASSISTANT_INTEGRATION`
- `MOTION_IN_OCEAN_PROMETHEUS_METRICS`
- `MOTION_IN_OCEAN_ENHANCED_FRAME_STATS`
- `MOTION_IN_OCEAN_REQUEST_TRACING`
- `MOTION_IN_OCEAN_NEW_STREAMING_API`
- `MOTION_IN_OCEAN_ALTERNATIVE_PROTOCOLS`
- `MIO_OCTOPRINT_COMPATIBILITY` (explicitly ignored with warning)
- `OCTOPRINT_COMPATIBILITY` (explicitly ignored with warning)
