# Feature Flags

Motion In Ocean currently exposes only **runtime-integrated** feature flags.

## Environment variable format

Use canonical `MIO_` names:

```bash
MIO_<FLAG_NAME>=true|false
```

Legacy aliases are documented only for flags where code still supports them:

- `MOCK_CAMERA` → `MIO_MOCK_CAMERA`
- `OCTOPRINT_COMPATIBILITY` → `MIO_OCTOPRINT_COMPATIBILITY`

## API contract (`GET /api/feature-flags`)

`/api/feature-flags` returns a **flat mapping** produced directly by
`feature_flags.get_all_flags()` in `main.py`.

Example response:

```json
{
  "MOCK_CAMERA": false,
  "OCTOPRINT_COMPATIBILITY": false
}
```

## Active flags

## CORS configuration (migrated from feature flag)

CORS is now configured via `MIO_CORS_ORIGINS` in runtime config, not the feature-flag registry.

- Empty/unset `MIO_CORS_ORIGINS` → CORS disabled
- `MIO_CORS_ORIGINS=*` → allow all origins
- `MIO_CORS_ORIGINS=https://a.example,https://b.example` → allow listed origins

`MIO_CORS_SUPPORT` is temporarily accepted for backward compatibility, logs a deprecation warning,
and is mapped only when `MIO_CORS_ORIGINS` is unset.

### `MIO_MOCK_CAMERA` (default: `false`)

Uses mock camera frames in webcam mode when enabled.

- Legacy alias currently supported: `MOCK_CAMERA`

### `MIO_OCTOPRINT_COMPATIBILITY` (default: `false`)

Uses OctoPrint-friendly MJPEG boundary formatting.

- Legacy alias currently supported: `OCTOPRINT_COMPATIBILITY`

## Registry policy

Any new feature flag must have a concrete runtime read before it can be added to
`FeatureFlags._define_flags`. CI validates this via
`pi_camera_in_docker.feature_flag_usage_check`.

The current registry does not include placeholder flags; if a future flag is
registered before runtime wiring exists, it must be explicitly marked as **not
implemented yet** in this guide.
