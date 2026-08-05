/**
 * Render webcam configuration sections without owning application state.
 */

type ConfigValue = string | number;
type HealthState = "ok" | "warn" | "fail" | "unknown";

interface ConfigData {
  camera_settings?: {
    resolution?: [number, number];
    fps?: number;
    target_fps?: number;
    jpeg_quality?: number;
  };
  stream_control?: {
    max_stream_connections?: number;
    current_stream_connections?: number;
    max_frame_age_seconds?: number;
    cors_origins?: string;
  };
  runtime?: {
    camera_active?: boolean;
    mock_camera?: boolean;
    active_mock_fallback?: boolean;
    uptime_seconds?: number;
  };
  health_check?: Record<string, { state?: string } | undefined>;
  timestamp?: string;
}

interface ConfigContext {
  state: { streamConnections: { current: ConfigValue; max: ConfigValue } };
  setConfigValue: (_id: string, _value: ConfigValue) => void;
  formatBoolean: (_value: boolean | undefined) => string;
  formatUptime: (_value: number | undefined) => string;
  applyMockStreamMode: (_isMockModeActive: boolean, _isFallbackActive: boolean) => void;
  setHealthIndicator: (_id: string, _indicator: unknown) => void;
  normalizeHealthState: (_value: string) => HealthState;
  healthText: Record<HealthState, string>;
  updateConnectionDisplays: () => void;
}

/**
 * Render camera, stream, runtime, health, and timestamp configuration sections.
 *
 * @param {Object} data - Configuration payload returned by the webcam API.
 * @param {Object} context - Application state and rendering dependencies.
 * @returns {void}
 */
export function renderConfig(data: ConfigData, context: ConfigContext): void {
  const {
    state,
    setConfigValue,
    formatBoolean,
    formatUptime,
    applyMockStreamMode,
    setHealthIndicator,
    normalizeHealthState,
    healthText,
    updateConnectionDisplays,
  } = context;

  renderCameraSettings(data.camera_settings, setConfigValue);
  renderStreamControl(data.stream_control, state, setConfigValue, updateConnectionDisplays);
  renderRuntime(data.runtime, setConfigValue, formatBoolean, formatUptime, applyMockStreamMode);
  renderHealth(data.health_check, setHealthIndicator, normalizeHealthState, healthText);

  if (data.timestamp) {
    setConfigValue("config-timestamp", new Date(data.timestamp).toLocaleTimeString());
  }
}

function renderCameraSettings(
  cameraSettings: ConfigData["camera_settings"],
  setConfigValue: ConfigContext["setConfigValue"],
): void {
  if (!cameraSettings) return;
  setConfigValue(
    "config-resolution",
    cameraSettings.resolution
      ? `${cameraSettings.resolution[0]} × ${cameraSettings.resolution[1]}`
      : "--",
  );
  setConfigValue(
    "config-fps",
    cameraSettings.fps !== undefined ? `${cameraSettings.fps} FPS` : "--",
  );
  setConfigValue(
    "config-target-fps",
    cameraSettings.target_fps !== undefined ? `${cameraSettings.target_fps} FPS` : "--",
  );
  setConfigValue(
    "config-jpeg-quality",
    cameraSettings.jpeg_quality !== undefined ? `${cameraSettings.jpeg_quality}%` : "--",
  );
}

function renderStreamControl(
  streamControl: ConfigData["stream_control"],
  state: ConfigContext["state"],
  setConfigValue: ConfigContext["setConfigValue"],
  updateConnectionDisplays: ConfigContext["updateConnectionDisplays"],
): void {
  if (!streamControl) return;
  setConfigValue("config-max-connections", streamControl.max_stream_connections ?? "--");
  setConfigValue("config-current-connections", streamControl.current_stream_connections ?? "--");
  setConfigValue(
    "config-max-frame-age",
    streamControl.max_frame_age_seconds !== undefined
      ? `${streamControl.max_frame_age_seconds}s`
      : "--",
  );
  setConfigValue(
    "config-cors",
    typeof streamControl.cors_origins === "string" && streamControl.cors_origins.length > 0
      ? streamControl.cors_origins
      : "disabled",
  );
  state.streamConnections.current = streamControl.current_stream_connections ?? "--";
  state.streamConnections.max = streamControl.max_stream_connections ?? "--";
  updateConnectionDisplays();
}

function renderRuntime(
  runtime: ConfigData["runtime"],
  setConfigValue: ConfigContext["setConfigValue"],
  formatBoolean: ConfigContext["formatBoolean"],
  formatUptime: ConfigContext["formatUptime"],
  applyMockStreamMode: ConfigContext["applyMockStreamMode"],
): void {
  if (!runtime) return;
  setConfigValue("config-camera-active", formatBoolean(runtime.camera_active));
  setConfigValue("config-mock-camera", formatBoolean(runtime.mock_camera));
  setConfigValue("config-uptime", formatUptime(runtime.uptime_seconds));
  applyMockStreamMode(
    runtime.mock_camera === true || runtime.active_mock_fallback === true,
    runtime.active_mock_fallback === true,
  );
}

function renderHealth(
  healthCheck: ConfigData["health_check"],
  setHealthIndicator: ConfigContext["setHealthIndicator"],
  normalizeHealthState: ConfigContext["normalizeHealthState"],
  healthText: ConfigContext["healthText"],
): void {
  if (!healthCheck) return;
  const healthStates: string[] = [];
  const applyIndicator = (
    elementId: string,
    indicator: { state?: string } | undefined,
  ): void => {
    setHealthIndicator(elementId, indicator);
    if (indicator && typeof indicator.state === "string") {
      healthStates.push(indicator.state);
    }
  };
  applyIndicator("config-health-camera-pipeline", healthCheck.camera_pipeline);
  applyIndicator("config-health-stream-freshness", healthCheck.stream_freshness);
  applyIndicator("config-health-connection-capacity", healthCheck.connection_capacity);
  applyIndicator("config-health-mock-mode", healthCheck.mock_mode);

  const normalizedStates = healthStates.map(normalizeHealthState);
  const overallState = normalizedStates.includes("fail")
    ? "fail"
    : normalizedStates.includes("warn")
      ? "warn"
      : normalizedStates.includes("ok")
        ? "ok"
        : "unknown";
  setHealthIndicator("config-health-overall", {
    state: overallState,
    label: healthText[overallState],
    details:
      "Overall health derived from camera, stream freshness, connection capacity, and mock mode.",
  });
}
