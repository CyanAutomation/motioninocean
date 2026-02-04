# Motion in Ocean - Feature Flags Reference

This document describes all available feature flags for Motion in Ocean. Feature flags enable gradual rollouts of new features, optional capabilities, performance optimizations, and A/B testing.

## Overview

Feature flags are controlled via environment variables with the `MOTION_IN_OCEAN_` prefix. For example, to enable the `DEBUG_LOGGING` flag, set:

```bash
MOTION_IN_OCEAN_DEBUG_LOGGING=true
```

### Backward Compatibility

Some flags support legacy environment variable names for backward compatibility:

- `MOCK_CAMERA` → `MOTION_IN_OCEAN_MOCK_CAMERA`

Both the prefixed and legacy names work, with the prefixed name taking precedence.

### Valid Boolean Values

All feature flags accept the following values (case-insensitive):

- **True**: `true`, `1`, `t`, `yes`, `on`
- **False**: `false`, `0`, `f`, `no`, `off`

---

## Performance Flags

These flags control performance optimizations and resource usage strategies.

### MOTION_IN_OCEAN_QUALITY_ADAPTATION

**Status**: Experimental  
**Default**: `false`  
**Description**: Enable automatic JPEG quality adaptation based on network conditions.

When enabled, the application adjusts JPEG quality dynamically to optimize for:

- Bandwidth-constrained networks (lower quality)
- High-speed networks (higher quality)

**Use Cases**:

- Serving streams over slow home networks
- Variable network conditions

**Example**:

```bash
MOTION_IN_OCEAN_QUALITY_ADAPTATION=true
```

---

### MOTION_IN_OCEAN_FPS_THROTTLE_ADAPTIVE

**Status**: Experimental  
**Default**: `false`  
**Description**: Enable adaptive FPS throttling based on client capabilities.

When enabled, the system throttles frames independently per client based on:

- Detected client download speed
- Connection type (LAN vs WAN)

**Use Cases**:

- Multi-client deployments with varying network speeds
- Reducing bandwidth for resource-constrained clients

---

### MOTION_IN_OCEAN_FRAME_SIZE_OPTIMIZATION

**Status**: Stable  
**Default**: `true`  
**Description**: Enable frame size optimization for bandwidth-constrained networks.

This flag controls whether frame size limits are automatically calculated based on resolution and JPEG quality. When enabled, prevents oversized frames from consuming excessive memory.

**Use Cases**:

- Memory-constrained Raspberry Pi devices
- Preventing memory exhaustion in edge cases

---

## Optional Features

These flags enable optional or experimental features that may not be stable.

### MOTION_IN_OCEAN_MOCK_CAMERA

**Status**: Stable  
**Default**: `false`  
**Legacy Variable**: `MOCK_CAMERA`  
**Description**: Use mock camera for testing without real hardware.

When enabled, generates synthetic black frames instead of reading from actual camera hardware. Useful for:

- Testing in non-Docker environments
- CI/CD pipelines
- Development without Raspberry Pi

**Example**:

```bash
MOTION_IN_OCEAN_MOCK_CAMERA=true
```

---

### MOTION_IN_OCEAN_MOTION_DETECTION

**Status**: Experimental  
**Default**: `false`  
**Description**: Enable motion detection hooks for frame analysis.

Adds frame-level motion detection capabilities and hooks for custom processing.

**Note**: This feature is under development.

---

### MOTION_IN_OCEAN_FRAME_RECORDING

**Status**: Experimental  
**Default**: `false`  
**Description**: Enable frame recording/buffering to disk.

When enabled, records frames to disk for replay or analysis.

**Note**: This feature is under development and may consume significant disk space.

---

## Hardware Optimization Flags

These flags optimize behavior for specific Raspberry Pi models.

### MOTION_IN_OCEAN_PI3_OPTIMIZATION

**Status**: Experimental  
**Default**: `false`  
**Description**: Enable Pi 3-specific optimizations (lower resolution, reduced FPS).

When enabled, automatically applies recommended settings for Raspberry Pi 3:

- Resolution: 1280x720 or lower
- FPS: 25fps maximum
- JPEG Quality: 80

Reduces CPU and memory pressure on older hardware.

---

### MOTION_IN_OCEAN_PI5_OPTIMIZATION

**Status**: Experimental  
**Default**: `false`  
**Description**: Enable Pi 5-specific optimizations (higher resolution, increased FPS).

When enabled, automatically applies recommended settings for Raspberry Pi 5:

- Resolution: 2592x1944 or higher
- FPS: 60fps or higher
- JPEG Quality: 95

Leverages newer hardware capabilities.

---

### MOTION_IN_OCEAN_MULTI_CAMERA_SUPPORT

**Status**: Experimental  
**Default**: `false`  
**Description**: Enable support for multiple camera inputs.

**Note**: This feature is under development and not yet available.

---

## Developer Tools

These flags enable logging, profiling, and debugging features.

### MOTION_IN_OCEAN_DEBUG_LOGGING

**Status**: Stable  
**Default**: `false`  
**Description**: Enable DEBUG-level logging for detailed diagnostics.

When enabled, sets logging level to DEBUG, producing verbose logs suitable for troubleshooting.

**Example**:

```bash
MOTION_IN_OCEAN_DEBUG_LOGGING=true
```

---

### MOTION_IN_OCEAN_TRACE_LOGGING

**Status**: Experimental  
**Default**: `false`  
**Description**: Enable TRACE-level logging with function entry/exit points.

When enabled, logs detailed function-level execution traces (even more verbose than DEBUG).

---

### MOTION_IN_OCEAN_PERFORMANCE_PROFILING

**Status**: Experimental  
**Default**: `false`  
**Description**: Enable CPU/memory profiling for performance analysis.

When enabled, collects performance metrics including:

- CPU usage per operation
- Memory allocation patterns
- Frame processing times

Outputs profiling data to logs.

---

### MOTION_IN_OCEAN_DEVELOPMENT_MODE

**Status**: Experimental  
**Default**: `false`  
**Description**: Enable development mode with relaxed validation and verbose output.

When enabled:

- Disables some security checks
- Produces more verbose logs
- Allows testing of unfinished features

**Warning**: Do NOT enable in production.

**Example**:

```bash
MOTION_IN_OCEAN_DEVELOPMENT_MODE=true
```

---

## Integration Compatibility

These flags enable compatibility modes for specific integrations.

### MOTION_IN_OCEAN_CORS_SUPPORT

**Status**: Stable  
**Default**: `true`  
**Description**: Enable CORS headers for cross-origin requests.

When enabled, allows cross-origin requests from web browsers. Useful for:

- Home Assistant integration
- Dashboard web interfaces
- Accessing camera stream from different domains

When disabled, CORS headers are not sent (useful for strict security policies).

**Example** (disable CORS):

```bash
MOTION_IN_OCEAN_CORS_SUPPORT=false
```

---

### MOTION_IN_OCEAN_OCTOPRINT_COMPATIBILITY

**Status**: Experimental  
**Default**: `false`  
**Description**: Enable OctoPrint camera format compatibility mode.

When enabled, adjusts stream format and endpoints for OctoPrint webcam plugins.

---

### MOTION_IN_OCEAN_HOME_ASSISTANT_INTEGRATION

**Status**: Experimental  
**Default**: `false`  
**Description**: Enable Home Assistant-specific endpoint optimizations.

When enabled, optimizes stream quality and buffering for Home Assistant's camera integration.

---

## Observability

These flags control metrics collection and observability features.

### MOTION_IN_OCEAN_PROMETHEUS_METRICS

**Status**: Experimental  
**Default**: `false`  
**Description**: Enable Prometheus-format metrics export.

When enabled, the `/metrics` endpoint returns data in Prometheus text format instead of JSON, for compatibility with Prometheus scrapers.

**Example**:

```bash
MOTION_IN_OCEAN_PROMETHEUS_METRICS=true
```

---

### MOTION_IN_OCEAN_ENHANCED_FRAME_STATS

**Status**: Experimental  
**Default**: `false`  
**Description**: Enable per-frame processing time statistics.

When enabled, tracks and logs processing time for each frame, useful for:

- Performance analysis
- Detecting bottlenecks
- Identifying slow frames

---

### MOTION_IN_OCEAN_REQUEST_TRACING

**Status**: Experimental  
**Default**: `false`  
**Description**: Enable detailed request lifecycle tracing.

When enabled, logs complete lifecycle of each HTTP request including:

- Request arrival and routing
- Stream client connection/disconnection
- Response timing

Useful for debugging streaming issues.

---

## Gradual Rollout

These flags enable new APIs and features as they're developed.

### MOTION_IN_OCEAN_NEW_STREAMING_API

**Status**: Experimental  
**Default**: `false`  
**Description**: Enable new streaming API endpoints (v2).

When enabled, enables experimental v2 API endpoints alongside v1 endpoints for backward compatibility testing.

**New Endpoints** (when enabled):

- `/api/v2/stream` - Enhanced streaming endpoint
- `/api/v2/config` - New configuration interface

---

### MOTION_IN_OCEAN_ALTERNATIVE_PROTOCOLS

**Status**: Experimental  
**Default**: `false`  
**Description**: Enable alternative streaming protocols (RTSP, HLS, WebRTC).

When enabled, adds support for additional streaming protocols:

- **RTSP**: `/stream.rtsp` (Real Time Streaming Protocol)
- **HLS**: `/stream.m3u8` (HTTP Live Streaming)
- **WebRTC**: `/api/stream/webrtc` (WebRTC streaming)

Useful for compatibility with older clients or specialized applications.

---

## API Endpoint

You can query all feature flags via the `/api/feature-flags` endpoint:

```bash
curl http://localhost:8000/api/feature-flags | jq
```

**Response Format**:

```json
{
  "summary": {
    "Performance": {
      "QUALITY_ADAPTATION": false,
      "FPS_THROTTLE_ADAPTIVE": false,
      ...
    },
    "Experimental": { ... },
    ...
  },
  "flags": {
    "MOCK_CAMERA": {
      "enabled": false,
      "default": false,
      "category": "Experimental",
      "description": "Use mock camera for testing without real hardware.",
    },
    ...
  },
  "timestamp": "2026-02-04T12:34:56.789012"
}
```

---

## Usage Examples

### Development Setup

```bash
export MOTION_IN_OCEAN_DEBUG_LOGGING=true
export MOTION_IN_OCEAN_MOCK_CAMERA=true
export MOTION_IN_OCEAN_DEVELOPMENT_MODE=true
export MOTION_IN_OCEAN_PERFORMANCE_PROFILING=true
```

### Production Optimized

```bash
export MOTION_IN_OCEAN_FRAME_SIZE_OPTIMIZATION=true
export MOTION_IN_OCEAN_CORS_SUPPORT=true
export MOTION_IN_OCEAN_HOME_ASSISTANT_INTEGRATION=true
```

### Edge Detection Testing

```bash
export MOTION_IN_OCEAN_DEBUG_LOGGING=true
```

### Performance Analysis

```bash
export MOTION_IN_OCEAN_PERFORMANCE_PROFILING=true
export MOTION_IN_OCEAN_ENHANCED_FRAME_STATS=true
export MOTION_IN_OCEAN_REQUEST_TRACING=true
export MOTION_IN_OCEAN_DEBUG_LOGGING=true
```

---

## Best Practices

1. **Production**: Keep experimental flags disabled. Use only stable flags.
2. **Testing**: Enable `DEBUG_LOGGING` and relevant testing flags.
3. **Performance Analysis**: Enable profiling flags together for comprehensive metrics.
4. **Integration**: Use specific integration flags (HOME_ASSISTANT_INTEGRATION, OCTOPRINT_COMPATIBILITY) rather than general flags.
5. **Monitoring**: Check `/api/feature-flags` regularly to verify flag state.

---

## See Also

- [README.md](../README.md) - Project overview
- [main.py](../pi_camera_in_docker/main.py) - Feature flag integration
- [feature_flags.py](../pi_camera_in_docker/feature_flags.py) - Feature flag implementation
