/**
 * Render webcam metrics without owning application state or DOM discovery.
 */

interface MetricsResponse {
  camera_active?: boolean;
  current_fps?: number;
  uptime_seconds?: number;
  frames_captured?: number;
  last_frame_age_seconds?: number;
  max_frame_age_seconds?: number;
  resolution?: number[];
}

interface MetricsElements {
  fpsValue: HTMLElement | null;
  chipFps: HTMLElement | null;
  performanceRiskValue: HTMLElement | null;
  uptimeValue: HTMLElement | null;
  framesRiskDetail: HTMLElement | null;
  lastFrameAgeValue: HTMLElement | null;
  lastFrameRiskValue: HTMLElement | null;
  maxFrameAgeValue: HTMLElement | null;
  maxFrameRiskValue: HTMLElement | null;
  streamRiskValue: HTMLElement | null;
  resolutionValue: HTMLElement | null;
  lastUpdated: HTMLElement | null;
}

interface MetricsContext {
  state: { elements: MetricsElements };
  setConnectionStatus: (status: "stale" | "connected" | "inactive", text: string) => void;
  resetBackoff: () => void;
  increaseBackoff: () => void;
  formatUptime: (seconds: number | undefined) => string;
  formatNumber: (value: number | undefined) => string;
  formatSeconds: (value: number | undefined) => string;
  updateConnectionDisplays: () => void;
}

/**
 * Render the metrics response into the webcam status panel.
 *
 * @param {Object} data - Metrics payload returned by the webcam API.
 * @param {Object} context - Application state and rendering dependencies.
 * @returns {void}
 */
export function renderMetrics(data: MetricsResponse, context: MetricsContext): void {
  const {
    state,
    setConnectionStatus,
    resetBackoff,
    increaseBackoff,
    formatUptime,
    formatNumber,
    formatSeconds,
    updateConnectionDisplays,
  } = context;
  const cameraActive = data.camera_active === true;
  const lastFrameAge = Number(data.last_frame_age_seconds);
  const maxFrameAge = Number(data.max_frame_age_seconds);
  const hasFrameAge = Number.isFinite(lastFrameAge);
  const hasMaxFrameAge = Number.isFinite(maxFrameAge);
  const isStale = cameraActive && hasFrameAge && hasMaxFrameAge && lastFrameAge > maxFrameAge;
  const statusText = cameraActive ? (isStale ? "Stale stream" : "Connected") : "Camera inactive";
  const statusState = cameraActive ? (isStale ? "stale" : "connected") : "inactive";

  setConnectionStatus(statusState, statusText);
  if (statusState === "connected") {
    resetBackoff();
  } else {
    increaseBackoff();
  }

  const fps = data.current_fps ? data.current_fps.toFixed(1) : "0.0";
  setText(state.elements.fpsValue, fps);
  setText(state.elements.chipFps, `Current FPS: ${fps}`);
  setText(state.elements.performanceRiskValue, `${fps} FPS`);
  setText(state.elements.uptimeValue, formatUptime(data.uptime_seconds));
  setText(state.elements.framesRiskDetail, formatNumber(data.frames_captured));
  setText(state.elements.lastFrameAgeValue, formatSeconds(data.last_frame_age_seconds));
  setText(state.elements.lastFrameRiskValue, formatSeconds(data.last_frame_age_seconds));
  setText(state.elements.maxFrameAgeValue, formatSeconds(data.max_frame_age_seconds));
  setText(state.elements.maxFrameRiskValue, formatSeconds(data.max_frame_age_seconds));
  setText(state.elements.streamRiskValue, statusText);

  if (state.elements.resolutionValue && data.resolution && Array.isArray(data.resolution)) {
    state.elements.resolutionValue.textContent = `${data.resolution[0]} × ${data.resolution[1]}`;
  }
  if (state.elements.lastUpdated) {
    state.elements.lastUpdated.textContent = `Updated: ${new Date().toLocaleTimeString()}`;
  }
  updateConnectionDisplays();
}

function setText(element: HTMLElement | null | undefined, value: string): void {
  if (element) {
    element.textContent = value;
  }
}
