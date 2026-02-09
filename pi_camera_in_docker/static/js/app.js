/**
 * motion-in-ocean - Camera Stream Application
 * Real-time stats, fullscreen, refresh, and connection monitoring
 */

const state = {
  updateInterval: null,
  baseUpdateFrequency: 2000,
  updateFrequency: 2000,
  maxUpdateFrequency: 30000,
  consecutiveFailures: 0,
  connectionTimeout: null,
  isConnected: false,
  statsCollapsed: false,
  statsInFlight: false,
  configInFlight: false,
  currentTab: "main",
  lastConfigUpdate: null,
  configPollingInterval: null,
  configTimestampInterval: null,
  configInitialLoadPending: false,
  configLoadingDelayTimer: null,
  configLoadingVisible: false,
  elements: {
    videoStream: null,
    statsPanel: null,
    configPanel: null,
    toggleStatsBtn: null,
    refreshBtn: null,
    fullscreenBtn: null,
    statusIndicator: null,
    statusText: null,
    fpsValue: null,
    uptimeValue: null,
    framesValue: null,
    lastFrameAgeValue: null,
    maxFrameAgeValue: null,
    resolutionValue: null,
    lastUpdated: null,
  },
};

/**
 * Initialize the application
 */
function init() {
  cacheElements();
  attachHandlers();
  startStatsUpdate();
  updateStats().catch((error) => console.error("Initial stats update failed:", error));
  updateConfig().catch((error) => console.error("Initial config update failed:", error));

  console.log("motion-in-ocean camera stream initialized");
}

/**
 * Cache DOM elements for performance
 */
function cacheElements() {
  state.elements.videoStream = document.getElementById("video-stream");
  state.elements.statsPanel = document.getElementById("stats-panel");
  state.elements.configPanel = document.getElementById("config-panel");
  state.elements.toggleStatsBtn = document.getElementById("toggle-stats-btn");
  state.elements.refreshBtn = document.getElementById("refresh-btn");
  state.elements.fullscreenBtn = document.getElementById("fullscreen-btn");
  state.elements.statusIndicator = document.getElementById("status-indicator");
  state.elements.statusText = document.getElementById("status-text");

  state.elements.fpsValue = document.getElementById("fps-value");
  state.elements.uptimeValue = document.getElementById("uptime-value");
  state.elements.framesValue = document.getElementById("frames-value");
  state.elements.lastFrameAgeValue = document.getElementById("last-frame-age-value");
  state.elements.maxFrameAgeValue = document.getElementById("max-frame-age-value");
  state.elements.resolutionValue = document.getElementById("resolution-value");
  state.elements.lastUpdated = document.getElementById("last-updated");

  // Config panel elements
  state.elements.configLoading = document.getElementById("config-loading");
  state.elements.configStatusIndicator = document.getElementById("config-status-indicator");
  state.elements.configStatusText = document.getElementById("config-status-text");
  state.elements.configLastUpdateTime = document.getElementById("config-last-update-time");
  state.elements.configErrorAlert = document.getElementById("config-error-alert");
  state.elements.configErrorMessage = document.getElementById("config-error-message");
}

/**
 * Attach event listeners
 */
function attachHandlers() {
  if (state.elements.toggleStatsBtn) {
    state.elements.toggleStatsBtn.addEventListener("click", toggleStats);
  }

  if (state.elements.refreshBtn) {
    state.elements.refreshBtn.addEventListener("click", refreshStream);
  }

  if (state.elements.fullscreenBtn) {
    state.elements.fullscreenBtn.addEventListener("click", toggleFullscreen);
  }

  if (state.elements.videoStream) {
    state.elements.videoStream.addEventListener("load", onStreamLoad);
    state.elements.videoStream.addEventListener("error", onStreamError);
  }

  // Tab navigation handlers
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tab = btn.getAttribute("data-tab");
      switchTab(tab);
    });
  });

  // Config group toggle handlers
  document.querySelectorAll(".config-group-toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
      const group = btn.getAttribute("data-group");
      toggleConfigGroup(group);
    });
  });

  document.addEventListener("fullscreenchange", onFullscreenChange);
  document.addEventListener("webkitfullscreenchange", onFullscreenChange);
  document.addEventListener("mozfullscreenchange", onFullscreenChange);
  document.addEventListener("MSFullscreenChange", onFullscreenChange);

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      stopStatsUpdate();
    } else {
      startStatsUpdate();
      if (!state.statsCollapsed && state.currentTab === "main") {
        updateStats().catch((error) => console.error("Stats update failed:", error));
      } else if (state.currentTab === "config") {
        updateConfig().catch((error) => console.error("Config update failed:", error));
      }
    }
  });
}

/**
 * Fetch and update stats from /metrics endpoint
 */
async function updateStats() {
  if (state.statsInFlight) return;
  if (state.statsCollapsed || document.hidden) return;

  try {
    state.statsInFlight = true;
    try {
      const data = await fetchMetrics();
      renderMetrics(data);
    } catch (error) {
      if (error && error.name === "AbortError") {
        console.warn("Stats request timed out, will retry.");
        increaseBackoff();
        return;
      }

      console.error("Failed to fetch stats:", error);
      setConnectionStatus("disconnected", "Disconnected");
      increaseBackoff();

      if (state.elements.fpsValue) {
        state.elements.fpsValue.textContent = "--";
      }

      if (state.elements.uptimeValue) {
        state.elements.uptimeValue.textContent = "--";
      }

      if (state.elements.framesValue) {
        state.elements.framesValue.textContent = "--";
      }

      if (state.elements.lastFrameAgeValue) {
        state.elements.lastFrameAgeValue.textContent = "--";
      }

      if (state.elements.maxFrameAgeValue) {
        state.elements.maxFrameAgeValue.textContent = "--";
      }

      if (state.elements.resolutionValue) {
        state.elements.resolutionValue.textContent = "--";
      }

      if (state.elements.lastUpdated) {
        state.elements.lastUpdated.textContent = "--";
      }

      return;
    }
  } finally {
    state.statsInFlight = false;
  }
}

/**
 * Toggle stats panel visibility (mobile)
 */
function toggleStats() {
  state.statsCollapsed = !state.statsCollapsed;

  if (state.elements.statsPanel) {
    state.elements.statsPanel.classList.toggle("collapsed", state.statsCollapsed);
  }

  if (state.elements.toggleStatsBtn) {
    state.elements.toggleStatsBtn.textContent = state.statsCollapsed ? "▼" : "▲";
  }

  if (state.statsCollapsed) {
    stopStatsUpdate();
  } else {
    startStatsUpdate();
    updateStats().catch((error) => console.error("Stats update failed:", error));
  }
}

/**
 * Refresh video stream
 */
function refreshStream() {
  if (!state.elements.videoStream) return;

  const streamUrl = state.elements.videoStream.src.split("?")[0];
  state.elements.videoStream.src = `${streamUrl}?t=${Date.now()}`;

  if (state.elements.refreshBtn) {
    state.elements.refreshBtn.style.transform = "rotate(360deg)";
    setTimeout(() => {
      state.elements.refreshBtn.style.transform = "";
    }, 300);
  }
}

/**
 * Toggle fullscreen mode
 */
function toggleFullscreen() {
  const container = document.querySelector(".video-container");
  if (!container) return;

  if (
    !document.fullscreenElement &&
    !document.webkitFullscreenElement &&
    !document.mozFullScreenElement &&
    !document.msFullscreenElement
  ) {
    if (container.requestFullscreen) {
      container.requestFullscreen();
    } else if (container.webkitRequestFullscreen) {
      container.webkitRequestFullscreen();
    } else if (container.mozRequestFullScreen) {
      container.mozRequestFullScreen();
    } else if (container.msRequestFullscreen) {
      container.msRequestFullscreen();
    }
  } else if (document.exitFullscreen) {
    document.exitFullscreen();
  } else if (document.webkitExitFullscreen) {
    document.webkitExitFullscreen();
  } else if (document.mozCancelFullScreen) {
    document.mozCancelFullScreen();
  } else if (document.msExitFullscreen) {
    document.msExitFullscreen();
  }
}

/**
 * Handle fullscreen change events
 */
function onFullscreenChange() {
  const isFullscreen = !!(
    document.fullscreenElement ||
    document.webkitFullscreenElement ||
    document.mozFullScreenElement ||
    document.msFullscreenElement
  );

  if (state.elements.fullscreenBtn) {
    const btnText = state.elements.fullscreenBtn.querySelector(".control-btn-text");
    if (btnText) {
      btnText.textContent = isFullscreen ? "Exit Fullscreen" : "Fullscreen";
    }
    const btnIcon = state.elements.fullscreenBtn.querySelector(".control-btn-icon");
    if (btnIcon) {
      btnIcon.textContent = isFullscreen ? "⛶" : "⛶";
    }
  }
}

/**
 * Handle stream load event
 */
function onStreamLoad() {
  hideLoading();
  setConnectionStatus("connected", "Stream Connected");
}

/**
 * Handle stream error event
 */
function onStreamError() {
  console.error("Video stream error");
  setConnectionStatus("disconnected", "Stream Error");
  increaseBackoff();
}

/**
 * Set connection status
 */
function setConnectionStatus(status, text) {
  state.isConnected = status === "connected" || status === "stale";

  if (state.elements.statusIndicator) {
    state.elements.statusIndicator.className = "status-indicator";
    state.elements.statusIndicator.classList.add(status);
  }

  if (state.elements.statusText) {
    state.elements.statusText.textContent = text;
  }
}

/**
 * Start stats update interval
 */
function startStatsUpdate() {
  if (state.updateInterval) return;
  if (state.statsCollapsed || document.hidden) return;

  state.updateInterval = setInterval(() => {
    updateStats().catch((error) => console.error("Stats update failed:", error));
  }, state.updateFrequency);
}

/**
 * Stop stats update interval
 */
function stopStatsUpdate() {
  if (state.updateInterval) {
    clearInterval(state.updateInterval);
    state.updateInterval = null;
  }
}

/**
 * Adjust the stats polling frequency and restart the timer if needed.
 */
function setUpdateFrequency(nextFrequency) {
  if (state.updateFrequency === nextFrequency) return;
  state.updateFrequency = nextFrequency;
  if (state.updateInterval) {
    stopStatsUpdate();
    startStatsUpdate();
  }
}

/**
 * Increase polling backoff when failures or inactive streams occur.
 */
function increaseBackoff() {
  state.consecutiveFailures += 1;
  const nextFrequency = Math.min(
    state.baseUpdateFrequency * Math.pow(2, state.consecutiveFailures),
    state.maxUpdateFrequency,
  );
  setUpdateFrequency(nextFrequency);
}

/**
 * Reset polling backoff on successful, active streams.
 */
function resetBackoff() {
  if (state.consecutiveFailures === 0 && state.updateFrequency === state.baseUpdateFrequency) {
    return;
  }
  state.consecutiveFailures = 0;
  setUpdateFrequency(state.baseUpdateFrequency);
}

/**
 * Fetch stats from /metrics endpoint
 */
async function fetchMetrics() {
  const timeoutMs = 5000;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => {
    controller.abort();
  }, timeoutMs);

  try {
    const response = await fetch("/metrics", { signal: controller.signal });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } finally {
    clearTimeout(timeoutId);
  }
}

/**
 * Render metrics data in the UI
 */
function renderMetrics(data) {
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
  } else if (statusState === "inactive" || statusState === "stale") {
    increaseBackoff();
  }

  if (state.elements.fpsValue) {
    state.elements.fpsValue.textContent = data.current_fps ? data.current_fps.toFixed(1) : "0.0";
  }

  if (state.elements.uptimeValue) {
    state.elements.uptimeValue.textContent = formatUptime(data.uptime_seconds);
  }

  if (state.elements.framesValue) {
    state.elements.framesValue.textContent = formatNumber(data.frames_captured);
  }

  if (state.elements.lastFrameAgeValue) {
    state.elements.lastFrameAgeValue.textContent = formatSeconds(data.last_frame_age_seconds);
  }

  if (state.elements.maxFrameAgeValue) {
    state.elements.maxFrameAgeValue.textContent = formatSeconds(data.max_frame_age_seconds);
  }

  if (state.elements.resolutionValue) {
    if (data.resolution && Array.isArray(data.resolution)) {
      state.elements.resolutionValue.textContent = `${data.resolution[0]} × ${data.resolution[1]}`;
    }
  }

  if (state.elements.lastUpdated) {
    const now = new Date();
    state.elements.lastUpdated.textContent = `Updated: ${now.toLocaleTimeString()}`;
  }
}

/**
 * Format uptime in human-readable format
 */
function formatUptime(seconds) {
  if (!seconds || seconds < 0) return "0s";

  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  const parts = [];
  if (days > 0) parts.push(`${days}d`);
  if (hours > 0) parts.push(`${hours}h`);
  if (minutes > 0) parts.push(`${minutes}m`);
  if (secs > 0 || parts.length === 0) parts.push(`${secs}s`);

  return parts.join(" ");
}

/**
 * Format large numbers with commas
 */
function formatNumber(num) {
  if (num === null || num === undefined) return "0";
  return num.toLocaleString();
}

/**
 * Format seconds with a consistent precision
 */
function formatSeconds(seconds) {
  if (seconds === null || seconds === undefined) return "--";
  if (Number.isNaN(seconds)) return "--";
  return `${Number(seconds).toFixed(2)}s`;
}

/**
 * Hide loading overlay
 */
function hideLoading() {
  const loadingOverlay = document.querySelector(".loading-overlay");
  if (loadingOverlay) {
    loadingOverlay.style.opacity = "0";
    setTimeout(() => {
      loadingOverlay.remove();
    }, 300);
  }
}

/**
 * Switch between tabs (main/config)
 */
function switchTab(tabName) {
  const wasConfigTab = state.currentTab === "config";
  state.currentTab = tabName;

  // Update tab buttons
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.classList.remove("active");
    if (btn.getAttribute("data-tab") === tabName) {
      btn.classList.add("active");
    }
  });

  // Update visible panels
  const mainSection = document.querySelector(".video-section");
  const statsPanel = state.elements.statsPanel;
  const configPanel = state.elements.configPanel;

  if (tabName === "main") {
    if (mainSection) mainSection.classList.remove("hidden");
    if (statsPanel) statsPanel.classList.remove("hidden");
    if (configPanel) configPanel.classList.add("hidden");

    // Resume stats updates and stop config refresh/timestamp updates
    if (!state.statsCollapsed) {
      startStatsUpdate();
    }
    stopConfigPolling();
    stopConfigTimestampUpdate();
  } else if (tabName === "config") {
    if (mainSection) mainSection.classList.add("hidden");
    if (statsPanel) statsPanel.classList.add("hidden");
    if (configPanel) configPanel.classList.remove("hidden");

    // Stop stats updates and start config refresh/timestamp updates
    stopStatsUpdate();

    if (!wasConfigTab) {
      state.configInitialLoadPending = true;
      updateConfig().catch((error) => console.error("Config update failed:", error));
      startConfigPolling();
      startConfigTimestampUpdate();
    }
  }
}

/**
 * Start periodic config polling
 */
function startConfigPolling() {
  if (state.configPollingInterval) return;

  state.configPollingInterval = setInterval(() => {
    updateConfig().catch((error) => console.error("Config update failed:", error));
  }, 2000);
}

/**
 * Stop periodic config polling
 */
function stopConfigPolling() {
  if (state.configPollingInterval) {
    clearInterval(state.configPollingInterval);
    state.configPollingInterval = null;
  }
}

/**
 * Toggle config group expansion/collapse
 */
function toggleConfigGroup(groupName) {
  const content = document.querySelector(`.config-group-content[data-group="${groupName}"]`);
  const btn = document.querySelector(`.config-group-toggle[data-group="${groupName}"]`);

  if (content && btn) {
    const isHidden = content.classList.contains("hidden");
    content.classList.toggle("hidden", !isHidden);
    btn.textContent = isHidden ? "▼" : "▶";
  }
}

/**
 * Fetch configuration from /api/config endpoint
 */
async function fetchConfig() {
  const timeoutMs = 5000;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => {
    controller.abort();
  }, timeoutMs);

  try {
    const response = await fetch("/api/config", { signal: controller.signal });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } finally {
    clearTimeout(timeoutId);
  }
}

/**
 * Update configuration display
 */
async function updateConfig() {
  if (state.configInFlight) return;
  if (state.currentTab !== "config" || document.hidden) return;

  const showHeavyLoading = state.configInitialLoadPending;

  try {
    state.configInFlight = true;

    if (showHeavyLoading && state.elements.configLoading) {
      state.configLoadingDelayTimer = setTimeout(() => {
        state.configLoadingVisible = true;
        state.elements.configLoading.classList.remove("hidden");
      }, 400);
      updateConfigStatus("fetching", "Loading configuration...");
    } else {
      updateConfigStatus("fetching", "Refreshing configuration...");
    }

    try {
      const data = await fetchConfig();
      renderConfig(data);

      // Update success state
      state.lastConfigUpdate = new Date();
      updateConfigStatus("ready", "Updated just now");
      updateConfigTimestampDisplay();

      // Hide error alert on success
      if (state.elements.configErrorAlert) {
        state.elements.configErrorAlert.classList.add("hidden");
      }
    } catch (error) {
      if (error && error.name === "AbortError") {
        console.warn("Config request timed out, will retry.");
        updateConfigStatus("error", "Request timed out");
        showConfigError("Configuration request timed out. Will retry automatically.");
        return;
      }

      console.error("Failed to fetch config:", error);
      clearConfigDisplay();
      updateConfigStatus("error", "Failed to load configuration");
      showConfigError(`Failed to load configuration: ${error.message || "Unknown error"}`);
      return;
    }
  } finally {
    state.configInFlight = false;
    state.configInitialLoadPending = false;

    if (state.configLoadingDelayTimer) {
      clearTimeout(state.configLoadingDelayTimer);
      state.configLoadingDelayTimer = null;
    }

    // Hide loading state
    if (state.configLoadingVisible && state.elements.configLoading) {
      state.elements.configLoading.classList.add("hidden");
      state.configLoadingVisible = false;
    }
  }
}

/**
 * Update config status indicator and message
 */
function updateConfigStatus(status, message) {
  if (state.elements.configStatusIndicator) {
    state.elements.configStatusIndicator.className = `config-status-dot ${status}`;
  }
  if (state.elements.configStatusText) {
    state.elements.configStatusText.textContent = message;
  }
}

/**
 * Update the "last updated" timestamp display
 */
function updateConfigTimestampDisplay() {
  if (!state.elements.configLastUpdateTime) return;

  const now = new Date();

  if (!state.lastConfigUpdate) {
    state.elements.configLastUpdateTime.textContent = "Now";
    return;
  }

  const diffSeconds = Math.floor((now - state.lastConfigUpdate) / 1000);

  if (diffSeconds < 5) {
    state.elements.configLastUpdateTime.textContent = "Just now";
  } else if (diffSeconds < 60) {
    state.elements.configLastUpdateTime.textContent = `${diffSeconds}s ago`;
  } else {
    const diffMinutes = Math.floor(diffSeconds / 60);
    state.elements.configLastUpdateTime.textContent = `${diffMinutes}m ago`;
  }
}

/**
 * Start periodic config timestamp updates
 */
function startConfigTimestampUpdate() {
  if (state.configTimestampInterval) return;

  // Update immediately and then every second
  updateConfigTimestampDisplay();
  state.configTimestampInterval = setInterval(() => {
    updateConfigTimestampDisplay();
  }, 1000);
}

/**
 * Stop periodic config timestamp updates
 */
function stopConfigTimestampUpdate() {
  if (state.configTimestampInterval) {
    clearInterval(state.configTimestampInterval);
    state.configTimestampInterval = null;
  }
}

/**
 * Show error alert in config panel
 */
function showConfigError(message) {
  if (!state.elements.configErrorAlert) return;

  if (state.elements.configErrorMessage) {
    state.elements.configErrorMessage.textContent = message;
  }
  state.elements.configErrorAlert.classList.remove("hidden");
}

/**
 * Render configuration data in the UI
 */
function renderConfig(data) {
  // Camera Settings
  if (data.camera_settings) {
    const cs = data.camera_settings;

    setConfigValue(
      "config-resolution",
      cs.resolution ? `${cs.resolution[0]} × ${cs.resolution[1]}` : "--",
    );
    setConfigValue("config-fps", cs.fps !== undefined ? `${cs.fps} FPS` : "--");
    setConfigValue(
      "config-target-fps",
      cs.target_fps !== undefined ? `${cs.target_fps} FPS` : "--",
    );
    setConfigValue(
      "config-jpeg-quality",
      cs.jpeg_quality !== undefined ? `${cs.jpeg_quality}%` : "--",
    );
  }

  // Stream Control
  if (data.stream_control) {
    const sc = data.stream_control;

    setConfigValue("config-max-connections", sc.max_stream_connections ?? "--");
    setConfigValue("config-current-connections", sc.current_stream_connections ?? "--");
    setConfigValue(
      "config-max-frame-age",
      sc.max_frame_age_seconds !== undefined ? `${sc.max_frame_age_seconds}s` : "--",
    );
    setConfigValue("config-cors", typeof sc.cors_origins === "string" ? sc.cors_origins : "*");
  }

  // Runtime
  if (data.runtime) {
    const rt = data.runtime;

    setConfigValue("config-camera-active", formatBoolean(rt.camera_active));
    setConfigValue("config-mock-camera", formatBoolean(rt.mock_camera));
    setConfigValue("config-uptime", formatUptime(rt.uptime_seconds));
  }

  // Limits
  if (data.limits) {
    const lim = data.limits;

    setConfigValue(
      "config-limit-resolution",
      lim.max_resolution ? `${lim.max_resolution[0]} × ${lim.max_resolution[1]}` : "--",
    );
    setConfigValue("config-limit-fps", lim.max_fps !== undefined ? `${lim.max_fps} FPS` : "--");
    setConfigValue(
      "config-limit-jpeg",
      lim.min_jpeg_quality && lim.max_jpeg_quality
        ? `${lim.min_jpeg_quality}% - ${lim.max_jpeg_quality}%`
        : "--",
    );
  }

  // Timestamp
  if (data.timestamp) {
    const date = new Date(data.timestamp);
    setConfigValue("config-timestamp", date.toLocaleTimeString());
  }
}

/**
 * Set a config value element's text content with badge styling for booleans
 */
function setConfigValue(elementId, value) {
  const element = document.getElementById(elementId);
  if (!element) return;

  element.textContent = value;

  // Apply badge styling for boolean values
  if (value === "Enabled" || value === "Yes") {
    element.className = "config-value config-badge enabled";
  } else if (value === "Disabled" || value === "No") {
    element.className = "config-value config-badge disabled";
  } else {
    element.className = "config-value";
  }
}

/**
 * Format boolean value as Yes/No with proper styling
 */
function formatBoolean(value) {
  if (value === null || value === undefined) return "--";
  return value ? "Enabled" : "Disabled";
}

/**
 * Clear all config display values
 */
function clearConfigDisplay() {
  const configValues = document.querySelectorAll("[data-config-value=\"true\"]");
  configValues.forEach((el) => {
    el.textContent = "--";
    el.className = "config-value";
  });
}

document.addEventListener("DOMContentLoaded", init);
