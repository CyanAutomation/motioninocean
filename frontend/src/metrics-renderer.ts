// @ts-nocheck

/**
 * Render webcam metrics without owning application state or DOM discovery.
 */

/**
 * Render the metrics response into the webcam status panel.
 *
 * @param {Object} data - Metrics payload returned by the webcam API.
 * @param {Object} context - Application state and rendering dependencies.
 * @returns {void}
 */
export function renderMetrics(data, context) {
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

function setText(element, value) {
  if (element) {
    element.textContent = value;
  }
}
