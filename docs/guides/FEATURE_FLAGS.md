# Feature Flags

Motion In Ocean currently exposes only **runtime-integrated** feature flags.

## Environment variable format

Use canonical `MIO_` names:

```bash
MIO_<FLAG_NAME>=true|false
```

Legacy aliases still supported:

- `MOCK_CAMERA` → `MIO_MOCK_CAMERA`
- `OCTOPRINT_COMPATIBILITY` → `MIO_OCTOPRINT_COMPATIBILITY`

## Active flags

### `MIO_MOCK_CAMERA` (default: `false`)

Uses mock camera frames in webcam mode when enabled.

### `MIO_CORS_SUPPORT` (default: `true`)

Controls CORS behavior in networking config.

### `MIO_OCTOPRINT_COMPATIBILITY` (default: `false`)

Uses OctoPrint-friendly MJPEG boundary formatting.

## Policy

Any new feature flag must have a concrete runtime read before it can be added to
`FeatureFlags._define_flags`. CI validates this via
`pi_camera_in_docker.feature_flag_usage_check`.
