/**
 * motion-in-ocean - Camera Stream Application
 * Real-time stats, fullscreen, refresh, and connection monitoring
 */

const REQUEST_TIMEOUT_MS = 5000;
const CONFIG_POLL_INTERVAL_MS = 5000;
const THEME_STORAGE_KEY = "webcam.theme";

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
  configInitialLoadPending: false,
  configLoadingDelayTimer: null,
  configLoadingVisible: false,
  setupInitialLoadPending: false,
  setupLoadingDelayTimer: null,
  setupLoadingVisible: false,
  setupFormState: {},
  setupDetectedDevices: {},
  streamConnections: {
    current: "--",
    max: "--",
  },
  elements: {
    videoStream: null,
    statsPanel: null,
    configPanel: null,
    setupPanel: null,
    toggleStatsBtn: null,
    refreshBtn: null,
    fullscreenBtn: null,
    refreshStreamHeaderBtn: null,
    statusIndicator: null,
    statusText: null,
    themeToggleBtn: null,
    themeIconMoon: null,
    themeIconSun: null,
    configRefreshBtn: null,
    fpsValue: null,
    uptimeValue: null,
    framesRiskDetail: null,
    lastFrameAgeValue: null,
    maxFrameAgeValue: null,
    resolutionValue: null,
    lastUpdated: null,
    viewTitle: null,
    viewSubtitle: null,
    connectionChipValue: null,
    performanceRiskValue: null,
    streamRiskValue: null,
    lastFrameRiskValue: null,
    maxFrameRiskValue: null,
    availabilityRiskValue: null,
    availabilityDetail: null,
    // Header status chips
    chipConnected: null,
    chipStale: null,
    chipInactive: null,
    chipFps: null,
  },
};

/**
 * Initialize the application
 */
function init() {
  cacheElements();
  attachHandlers();
  initializeTheme();
  updateViewMeta(state.currentTab);
  startStatsUpdate();
  updateStats().catch((error) => console.error("Initial stats update failed:", error));
  updateConfig().catch((error) => console.error("Initial config update failed:", error));

  console.log("motion-in-ocean camera stream initialized");
}

/**
 * Apply theme mode to webcam page.
 *
 * Persists selected mode in localStorage and updates toggle label.
 *
 * @param {string} theme - Theme name ("light" or "dark").
 * @returns {void}
 */
function applyTheme(theme) {
  const resolvedTheme = theme === "dark" ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", resolvedTheme);

  // Toggle moon/sun icons
  if (state.elements.themeIconMoon) {
    state.elements.themeIconMoon.style.display = resolvedTheme === "dark" ? "none" : "";
  }
  if (state.elements.themeIconSun) {
    state.elements.themeIconSun.style.display = resolvedTheme === "dark" ? "" : "none";
  }

  try {
    localStorage.setItem(THEME_STORAGE_KEY, resolvedTheme);
  } catch {
    // Ignore local storage failures.
  }
}

/**
 * Initialize theme from persisted user preference.
 *
 * Defaults to light theme when no preference exists.
 *
 * @returns {void}
 */
function initializeTheme() {
  let preferredTheme = "light";
  try {
    preferredTheme = localStorage.getItem(THEME_STORAGE_KEY) || "light";
  } catch {
    // Ignore local storage failures.
  }
  applyTheme(preferredTheme);
}

/**
 * Cache DOM elements for performance
 */
function cacheElements() {
  state.elements.videoStream = document.getElementById("video-stream");
  state.elements.statsPanel = document.getElementById("stats-panel");
  state.elements.configPanel = document.getElementById("config-panel");
  state.elements.settingsPanel = document.getElementById("settings-panel");
  state.elements.setupPanel = document.getElementById("setup-panel");
  state.elements.toggleStatsBtn = document.getElementById("toggle-stats-btn");
  state.elements.refreshBtn = document.getElementById("refresh-btn");
  state.elements.fullscreenBtn = document.getElementById("fullscreen-btn");
  state.elements.refreshStreamHeaderBtn = document.getElementById("refresh-stream-header-btn");
  state.elements.statusIndicator = document.getElementById("status-indicator");
  state.elements.statusText = document.getElementById("status-text");
  state.elements.themeToggleBtn = document.getElementById("theme-toggle-btn");
  state.elements.themeIconMoon = document.getElementById("theme-icon-moon");
  state.elements.themeIconSun = document.getElementById("theme-icon-sun");
  state.elements.configRefreshBtn = document.getElementById("config-refresh-btn");

  state.elements.fpsValue = document.getElementById("fps-value");
  state.elements.uptimeValue = document.getElementById("uptime-value");
  state.elements.framesRiskDetail = document.getElementById("frames-risk-detail");
  state.elements.lastFrameAgeValue = document.getElementById("last-frame-age-value");
  state.elements.maxFrameAgeValue = document.getElementById("max-frame-age-value");
  state.elements.resolutionValue = document.getElementById("resolution-value");
  state.elements.lastUpdated = document.getElementById("last-updated");
  state.elements.viewTitle = document.getElementById("webcam-view-title");
  state.elements.viewSubtitle = document.getElementById("webcam-view-subtitle");
  state.elements.connectionChipValue = document.getElementById("connection-chip-value");
  state.elements.performanceRiskValue = document.getElementById("performance-risk-value");
  state.elements.streamRiskValue = document.getElementById("stream-risk-value");
  state.elements.lastFrameRiskValue = document.getElementById("last-frame-risk-value");
  state.elements.maxFrameRiskValue = document.getElementById("max-frame-risk-value");
  state.elements.availabilityRiskValue = document.getElementById("availability-risk-value");
  state.elements.availabilityDetail = document.getElementById("availability-detail");

  // Header status chips
  state.elements.chipConnected = document.getElementById("chip-connected");
  state.elements.chipStale = document.getElementById("chip-stale");
  state.elements.chipInactive = document.getElementById("chip-inactive");
  state.elements.chipFps = document.getElementById("chip-fps");

  // Config panel elements
  state.elements.configLoading = document.getElementById("config-loading");
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

  if (state.elements.refreshStreamHeaderBtn) {
    state.elements.refreshStreamHeaderBtn.addEventListener("click", refreshStream);
  }

  if (state.elements.fullscreenBtn) {
    state.elements.fullscreenBtn.addEventListener("click", toggleFullscreen);
  }

  if (state.elements.themeToggleBtn) {
    state.elements.themeToggleBtn.addEventListener("click", () => {
      const currentTheme = document.documentElement.getAttribute("data-theme") || "light";
      applyTheme(currentTheme === "dark" ? "light" : "dark");
    });
  }

  if (state.elements.configRefreshBtn) {
    state.elements.configRefreshBtn.addEventListener("click", refreshConfigPanel);
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
      stopConfigPolling();
    } else {
      if (!state.statsCollapsed && state.currentTab === "main") {
        startStatsUpdate();
        updateStats().catch((error) => console.error("Stats update failed:", error));
      } else if (state.currentTab === "config") {
        startConfigPolling();
        updateConfig().catch((error) => console.error("Config update failed:", error));
      }

      assertSinglePollingMode();
    }
  });
}

/**
 * Ensure only one polling mode is active at a time.
 */
function assertSinglePollingMode() {
  const statsPollingActive = state.updateInterval !== null;
  const configPollingActive = state.configPollingInterval !== null;

  console.assert(
    !(statsPollingActive && configPollingActive),
    "Invalid polling state: stats and config polling are both active.",
  );
}

/**
 * Fetch and update stats from /metrics endpoint.
 *
 * Polls metrics data and renders to UI. Handles timeouts, errors, connection status.
 * Skips update if request already in flight, stats collapsed, or page hidden.
 * Updates backoff on error or timeout.
 *
 * @async
 * @returns {Promise<void>}
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

      if (state.elements.framesRiskDetail) {
        state.elements.framesRiskDetail.textContent = "--";
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

      if (state.elements.performanceRiskValue) {
        state.elements.performanceRiskValue.textContent = "--";
      }

      if (state.elements.streamRiskValue) {
        state.elements.streamRiskValue.textContent = "Offline";
      }

      if (state.elements.lastFrameRiskValue) {
        state.elements.lastFrameRiskValue.textContent = "--";
      }

      if (state.elements.maxFrameRiskValue) {
        state.elements.maxFrameRiskValue.textContent = "--";
      }

      if (state.elements.availabilityRiskValue) {
        state.elements.availabilityRiskValue.textContent = "Offline";
      }

      if (state.elements.availabilityDetail) {
        state.elements.availabilityDetail.textContent = "-- connections";
      }

      updateConnectionDisplays();

      return;
    }
  } finally {
    state.statsInFlight = false;
  }
}

/**
 * Toggle stats panel visibility and polling.
 *
 * Collapses/expands stats display, stops polling when collapsed,
 * resumes polling when expanded.
 *
 * @returns {void}
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
 * Refresh video stream with cache-busting query parameter.
 *
 * Resets stream src to force reload.
 * Animates refresh button on click.
 *
 * @returns {void}
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
 * Toggle fullscreen mode for video container.
 *
 * Supports cross-browser fullscreen API (webkit, moz, ms prefixes).
 * Exits fullscreen if already active, enters otherwise.
 *
 * @returns {void}
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
 * Handle stream load event.
 *
 * Hides loading overlay and sets connection status to connected.
 *
 * @returns {void}
 */
function onStreamLoad() {
  hideLoading();
  setConnectionStatus("connected", "Stream Connected");
  // Hide the status legend now that the stream is live
  const legend = document.getElementById("stream-status-legend");
  if (legend) {
    legend.classList.add("hidden");
  }
}

/**
 * Handle stream error event.
 *
 * Logs error, sets connection status to disconnected, increases polling backoff.
 *
 * @returns {void}
 */
function onStreamError() {
  console.error("Video stream error");
  setConnectionStatus("disconnected", "Stream Error");
  increaseBackoff();
}

/**
 * Set connection status indicator and text.
 *
 * Updates UI indicator class and text based on status (connected, disconnected, stale, inactive).
 * Sets state.isConnected based on status.
 *
 * @param {string} status - Status type ("connected", "disconnected", "stale", "inactive").
 * @param {string} text - Display text for status indicator.
 * @returns {void}
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

  // Drive header chips
  const isConnected = status === "connected";
  const isStale = status === "stale";
  const isInactive = status === "inactive" || status === "disconnected";

  if (state.elements.chipConnected) {
    state.elements.chipConnected.classList.toggle("hidden", !isConnected);
  }
  if (state.elements.chipStale) {
    state.elements.chipStale.classList.toggle("hidden", !isStale);
  }
  if (state.elements.chipInactive) {
    state.elements.chipInactive.classList.toggle("hidden", !isInactive);
  }

  // Update vc-connection item spin state
  const vcConnection = document.getElementById("vc-connection");
  if (vcConnection) {
    vcConnection.classList.toggle("is-connected", isConnected);
  }
}

/**
 * Start stats update interval.
 *
 * Sets up periodic updateStats() calls at current frequency.
 * Skips if interval already running, stats collapsed, or page hidden.
 *
 * @returns {void}
 */
function startStatsUpdate() {
  if (state.updateInterval) return;
  if (state.statsCollapsed || document.hidden) return;

  state.updateInterval = setInterval(() => {
    updateStats().catch((error) => console.error("Stats update failed:", error));
  }, state.updateFrequency);
}

/**
 * Stop stats update interval.
 *
 * Clears interval timer and resets interval ID.
 *
 * @returns {void}
 */
function stopStatsUpdate() {
  if (state.updateInterval) {
    clearInterval(state.updateInterval);
    state.updateInterval = null;
  }
}

/**
 * Set stats polling frequency and restart timer if active.
 *
 * Allows dynamic frequency adjustment. Stops and restarts interval if already running.
 *
 * @param {number} nextFrequency - Polling frequency in milliseconds.
 * @returns {void}
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
 * Increase polling backoff on errors/timeouts.
 *
 * Exponentially increases poll frequency (2^failures), capped at maxUpdateFrequency.
 *
 * @returns {void}
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
 * Reset polling backoff on successful stream.
 *
 * Returns to baseUpdateFrequency and clears failure counter.
 *
 * @returns {void}
 */
function resetBackoff() {
  if (state.consecutiveFailures === 0 && state.updateFrequency === state.baseUpdateFrequency) {
    return;
  }
  state.consecutiveFailures = 0;
  setUpdateFrequency(state.baseUpdateFrequency);
}

/**
 * Fetch metrics from /metrics endpoint with timeout.
 *
 * Fetches JSON metrics data with REQUEST_TIMEOUT_MS abort signal.
 * Throws if response not OK or timeout occurs.
 *
 * @async
 * @returns {Promise<Object>} Metrics data object with fps, uptime, frame counts, etc.
 * @throws {Error} If fetch fails, response not OK, or request times out.
 */
async function fetchMetrics() {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => {
    controller.abort();
  }, REQUEST_TIMEOUT_MS);

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
 * Render metrics data in UI elements.
 *
 * Updates FPS, uptime, frame counts, resolution, and connection status based on metrics.
 * Determines if stream is active, stale, or inactive and adjusts polling backoff.
 * Resets backoff on successful connection, increases on stale/inactive.
 *
 * @param {Object} data - Metrics data object from /metrics endpoint.
 * @returns {void}
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

  // Update FPS header chip
  if (state.elements.chipFps) {
    const fpsDisplay = data.current_fps ? data.current_fps.toFixed(1) : "0.0";
    state.elements.chipFps.textContent = `Current FPS: ${fpsDisplay}`;
  }

  if (state.elements.performanceRiskValue) {
    const fpsText = data.current_fps ? data.current_fps.toFixed(1) : "0.0";
    state.elements.performanceRiskValue.textContent = `${fpsText} FPS`;
  }

  if (state.elements.uptimeValue) {
    state.elements.uptimeValue.textContent = formatUptime(data.uptime_seconds);
  }

  if (state.elements.framesRiskDetail) {
    state.elements.framesRiskDetail.textContent = formatNumber(data.frames_captured);
  }

  if (state.elements.lastFrameAgeValue) {
    state.elements.lastFrameAgeValue.textContent = formatSeconds(data.last_frame_age_seconds);
  }

  if (state.elements.lastFrameRiskValue) {
    state.elements.lastFrameRiskValue.textContent = formatSeconds(data.last_frame_age_seconds);
  }

  if (state.elements.maxFrameAgeValue) {
    state.elements.maxFrameAgeValue.textContent = formatSeconds(data.max_frame_age_seconds);
  }

  if (state.elements.maxFrameRiskValue) {
    state.elements.maxFrameRiskValue.textContent = formatSeconds(data.max_frame_age_seconds);
  }

  if (state.elements.streamRiskValue) {
    state.elements.streamRiskValue.textContent = statusText;
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

  updateConnectionDisplays();
}

/**
 * Update connection indicators using the latest stream connection counts.
 *
 * Synchronizes the chip text, availability detail, and availability badge.
 *
 * @returns {void}
 */
function updateConnectionDisplays() {
  const current = formatConnectionValue(state.streamConnections.current);
  const max = formatConnectionValue(state.streamConnections.max);
  const label = `${current}/${max}`;

  if (state.elements.connectionChipValue) {
    state.elements.connectionChipValue.textContent = label;
  }

  if (state.elements.availabilityDetail) {
    state.elements.availabilityDetail.textContent = `${label} connections`;
  }

  if (state.elements.availabilityRiskValue) {
    state.elements.availabilityRiskValue.textContent = state.isConnected ? "Online" : "Offline";
    state.elements.availabilityRiskValue.dataset.status = state.isConnected ? "online" : "offline";
  }
}

/**
 * Normalize connection values for display.
 *
 * @param {number|string|null|undefined} value
 * @returns {string}
 */
function formatConnectionValue(value) {
  if (value === null || value === undefined) {
    return "--";
  }
  if (typeof value === "number") {
    return value.toString();
  }
  if (typeof value === "string" && value.trim().length > 0) {
    return value;
  }
  return "--";
}

/**
 * Format uptime seconds in human-readable format.
 *
 * Converts seconds to "Xd Yh Zm Ws" format (e.g., "2d 3h 4m 5s").
 *
 * @param {number} seconds - Uptime in seconds.
 * @returns {string} Formatted uptime string, or "0s" if invalid.
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
 * Format large numbers with locale-specific thousands separators.
 *
 * E.g., 1234567 → "1,234,567" (en-US locale).
 *
 * @param {number} num - Number to format.
 * @returns {string} Formatted number string.
 */
function formatNumber(num) {
  if (num === null || num === undefined) return "0";
  return num.toLocaleString();
}

/**
 * Format seconds with two decimal places.
 *
 * E.g., 1.234 seconds → "1.23s".
 *
 * @param {number} seconds - Seconds value.
 * @returns {string} Formatted seconds string, or "--" if invalid.
 */
function formatSeconds(seconds) {
  if (seconds === null || seconds === undefined) return "--";
  if (Number.isNaN(seconds)) return "--";
  return `${Number(seconds).toFixed(2)}s`;
}

/**
 * Hide loading overlay with fade-out animation.
 *
 * Fades out opacity over 300ms then removes element from DOM.
 *
 * @returns {void}
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
 * Switch between UI tabs (main/config/setup).
 *
 * Updates tab button state, shows/hides panels, starts/stops polling based on active tab.
 * Main tab: displays video stream and stats, resumes stats polling.
 * Config tab: displays settings panel, starts config refresh polling.
 * Setup tab: displays setup wizard, stops all polling.
 *
 * @param {string} tabName - Tab name ("main", "config", "setup").
 * @returns {void}
 */
function switchTab(tabName) {
  const wasConfigTab = state.currentTab === "config";
  const wasSetupTab = state.currentTab === "setup";
  state.currentTab = tabName;

  // Update tab buttons
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.classList.remove("active");
    if (btn.getAttribute("data-tab") === tabName) {
      btn.classList.add("active");
    }
  });

  updateViewMeta(tabName);

  // Update visible panels
  const mainSection = document.querySelector(".video-section");
  const statsPanel = state.elements.statsPanel;
  const configPanel = state.elements.configPanel;
  const settingsPanel = state.elements.settingsPanel;
  const setupPanel = state.elements.setupPanel;

  if (tabName === "main") {
    if (mainSection) mainSection.classList.remove("hidden");
    if (statsPanel) statsPanel.classList.remove("hidden");
    if (configPanel) configPanel.classList.add("hidden");
    if (settingsPanel) settingsPanel.classList.add("hidden");
    if (setupPanel) setupPanel.classList.add("hidden");

    // Resume stats updates and stop config refresh updates
    stopConfigPolling();

    if (!state.statsCollapsed) {
      startStatsUpdate();
    }
  } else if (tabName === "config") {
    if (mainSection) mainSection.classList.add("hidden");
    if (statsPanel) statsPanel.classList.add("hidden");
    if (configPanel) configPanel.classList.remove("hidden");
    if (settingsPanel) settingsPanel.classList.add("hidden");
    if (setupPanel) setupPanel.classList.add("hidden");

    // Stop stats updates and start config refresh/timestamp updates
    stopStatsUpdate();

    if (!wasConfigTab) {
      state.configInitialLoadPending = true;
      updateConfig().catch((error) => console.error("Config update failed:", error));
      startConfigPolling();
    }
  } else if (tabName === "settings") {
    if (mainSection) mainSection.classList.add("hidden");
    if (statsPanel) statsPanel.classList.add("hidden");
    if (configPanel) configPanel.classList.add("hidden");
    if (settingsPanel) settingsPanel.classList.remove("hidden");
    if (setupPanel) setupPanel.classList.add("hidden");

    // Stop all polling
    stopStatsUpdate();
    stopConfigPolling();
  } else if (tabName === "setup") {
    if (mainSection) mainSection.classList.add("hidden");
    if (statsPanel) statsPanel.classList.add("hidden");
    if (configPanel) configPanel.classList.add("hidden");
    if (settingsPanel) settingsPanel.classList.add("hidden");
    if (setupPanel) setupPanel.classList.remove("hidden");

    // Stop all polling
    stopStatsUpdate();
    stopConfigPolling();

    // Load setup tab if not already loaded
    if (!wasSetupTab) {
      state.setupInitialLoadPending = true;
      loadSetupTab().catch((error) => console.error("Setup tab load failed:", error));
    }
  }

  assertSinglePollingMode();
}

/**
 * Update view title and subtitle to reflect active webcam view.
 *
 * @param {string} tabName - Active view key.
 * @returns {void}
 */
function updateViewMeta(tabName) {
  const titleByTab = {
    main: "Stream",
    config: "Configuration",
    setup: "Set-Up",
    settings: "Runtime Settings",
  };
  const subtitleByTab = {
    main: "Camera Live Stream",
    config: "Resolution, FPS, and JPEG tuning",
    setup: "Guided setup and generated files",
    settings: "Check changes before saving. Reset restores defaults.",
  };

  if (state.elements.viewTitle) {
    state.elements.viewTitle.textContent = titleByTab[tabName] || "Stream";
  }
  if (state.elements.viewSubtitle) {
    state.elements.viewSubtitle.textContent = subtitleByTab[tabName] || "Camera Live Stream";
  }
}

/**
 * Start periodic config polling
 */
function startConfigPolling() {
  if (state.configPollingInterval) return;

  state.configPollingInterval = setInterval(() => {
    updateConfig().catch((error) => console.error("Config update failed:", error));
  }, CONFIG_POLL_INTERVAL_MS);
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
 * Trigger an immediate configuration refresh.
 *
 * Forces loading state behavior and reuses existing updateConfig error handling.
 *
 * @returns {void}
 */
function refreshConfigPanel() {
  state.configInitialLoadPending = true;
  updateConfig().catch((error) => console.error("Config update failed:", error));
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
  const controller = new AbortController();
  const timeoutId = setTimeout(() => {
    controller.abort();
  }, REQUEST_TIMEOUT_MS);

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
    }

    try {
      const data = await fetchConfig();
      renderConfig(data);

      // Update success state
      state.lastConfigUpdate = new Date();

      // Hide error alert on success
      if (state.elements.configErrorAlert) {
        state.elements.configErrorAlert.classList.add("hidden");
      }
    } catch (error) {
      if (error && error.name === "AbortError") {
        console.warn("Config request timed out, will retry.");
        showConfigError("Configuration request timed out. Will retry automatically.");
        return;
      }

      console.error("Failed to fetch config:", error);
      clearConfigDisplay();
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
 * Show error alert in config panel with message.
 *
 * Displays error message in config error alert element.
 *
 * @param {string} message - Error message to display.
 * @returns {void}
 */
function showConfigError(message) {
  if (!state.elements.configErrorAlert) return;

  if (state.elements.configErrorMessage) {
    state.elements.configErrorMessage.textContent = message;
  }
  state.elements.configErrorAlert.classList.remove("hidden");
}

/**
 * Render configuration data in UI elements.
 *
 * Displays camera settings, stream stats, hardware info, feature flags, and health status.
 * Updates resolution, FPS, quality, and other configuration values from API response.
 *
 * @param {Object} data - Configuration data object from /api/config endpoint.
 * @returns {void}
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
    setConfigValue(
      "config-cors",
      typeof sc.cors_origins === "string" && sc.cors_origins.length > 0
        ? sc.cors_origins
        : "disabled",
    );

    const currentConnections =
      typeof sc.current_stream_connections === "number"
        ? sc.current_stream_connections
        : (sc.current_stream_connections ?? "--");
    const maxConnections =
      typeof sc.max_stream_connections === "number"
        ? sc.max_stream_connections
        : (sc.max_stream_connections ?? "--");
    state.streamConnections.current = currentConnections;
    state.streamConnections.max = maxConnections;
    updateConnectionDisplays();
  }

  // Runtime
  if (data.runtime) {
    const rt = data.runtime;

    setConfigValue("config-camera-active", formatBoolean(rt.camera_active));
    setConfigValue("config-mock-camera", formatBoolean(rt.mock_camera));
    setConfigValue("config-uptime", formatUptime(rt.uptime_seconds));
  }

  // Health Check
  if (data.health_check) {
    const hc = data.health_check;
    const healthStates = [];

    const applyIndicator = (elementId, indicator) => {
      setHealthIndicator(elementId, indicator);
      if (indicator && typeof indicator.state === "string") {
        healthStates.push(indicator.state);
      }
    };

    applyIndicator("config-health-camera-pipeline", hc.camera_pipeline);
    applyIndicator("config-health-stream-freshness", hc.stream_freshness);
    applyIndicator("config-health-connection-capacity", hc.connection_capacity);
    applyIndicator("config-health-mock-mode", hc.mock_mode);

    const normalizedStates = healthStates.map(normalizeHealthState);
    let overallState = "unknown";
    if (normalizedStates.includes("fail")) {
      overallState = "fail";
    } else if (normalizedStates.includes("warn")) {
      overallState = "warn";
    } else if (normalizedStates.includes("ok")) {
      overallState = "ok";
    }

    setHealthIndicator("config-health-overall", {
      state: overallState,
      label: HEALTH_TEXT[overallState],
      details:
        "Overall health derived from camera, stream freshness, connection capacity, and mock mode.",
    });
  }

  // Timestamp
  if (data.timestamp) {
    const date = new Date(data.timestamp);
    setConfigValue("config-timestamp", date.toLocaleTimeString());
  }
}

const HEALTH_TEXT = {
  ok: "OK",
  warn: "Warning",
  fail: "Failing",
  unknown: "Unknown",
};

function normalizeHealthState(stateValue) {
  const normalized = String(stateValue || "").toLowerCase();

  if (["ok", "pass", "healthy", "ready"].includes(normalized)) return "ok";
  if (["warn", "warning", "degraded"].includes(normalized)) return "warn";
  if (["fail", "error", "failed", "down", "unhealthy"].includes(normalized)) return "fail";
  return "unknown";
}

function setHealthIndicator(elementId, indicator) {
  const element = document.getElementById(elementId);
  if (!element) return;

  const stateKey = normalizeHealthState(indicator?.state);
  const labelText =
    typeof indicator?.label === "string" && indicator.label.trim().length > 0
      ? indicator.label
      : HEALTH_TEXT[stateKey];

  element.textContent = labelText;
  element.className = `config-value health-indicator health-${stateKey}`;
  element.setAttribute("data-health-state", stateKey);

  const detailText = typeof indicator?.details === "string" ? indicator.details.trim() : "";
  if (detailText) {
    element.title = detailText;
  } else {
    element.removeAttribute("title");
  }
}

/**
 * Set config value element text with badge styling for boolean values.
 *
 * Updates element text content and applies badge classes for Enabled/Disabled/Yes/No values.
 * Removes badge class for other values.
 *
 * @param {string} elementId - HTML element ID to update.
 * @param {string} value - Value to display.
 * @returns {void}
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
 * Format boolean value as "Enabled" or "Disabled".
 *
 * Returns "Enabled" for true, "Disabled" for false, "--" for null/undefined.
 *
 * @param {boolean|null|undefined} value - Boolean value to format.
 * @returns {string} Formatted string ("Enabled", "Disabled", or "--").
 */
function formatBoolean(value) {
  if (value === null || value === undefined) return "--";
  return value ? "Enabled" : "Disabled";
}

/**
 * Clear all config display values to "--".
 *
 * Resets all config value elements, removes health indicators, resets health state.
 *
 * @returns {void}
 */
function clearConfigDisplay() {
  const configValues = document.querySelectorAll('[data-config-value="true"]');
  configValues.forEach((el) => {
    el.textContent = "--";
    el.className = "config-value";
    if (el.id && el.id.startsWith("config-health-")) {
      el.classList.add("health-indicator", "health-unknown");
      el.setAttribute("data-health-state", "unknown");
    } else {
      el.removeAttribute("data-health-state");
    }
    el.removeAttribute("title");
  });

  state.streamConnections.current = "--";
  state.streamConnections.max = "--";
  updateConnectionDisplays();
}

/* ==========================================
   Setup Tab Functions
   ========================================== */

const setupWizard = {
  storageKey: "motioninocean.setupWizard.v1",
  steps: ["environment", "preset", "review", "generate"],
  currentStep: "environment",
  expertMode: false,
  initialized: false,
};

/**
 * Load wizard state from localStorage.
 *
 * Retrieves and parses wizard state JSON from setupWizard.storageKey.
 * Returns empty object if missing or parse fails.
 *
 * @returns {Object} Wizard state object or empty object.
 */
function getWizardStateFromStorage() {
  try {
    const raw = localStorage.getItem(setupWizard.storageKey);
    return raw ? JSON.parse(raw) : {};
  } catch (_error) {
    return {};
  }
}

/**
 * Save wizard state to localStorage.
 *
 * Persists current step, expert mode, environment selections, preset, and form fields.
 * Enables state recovery on page reload.
 *
 * @returns {void}
 */
function saveWizardState() {
  const payload = {
    currentStep: setupWizard.currentStep,
    expertMode: setupWizard.expertMode,
    environment: {
      piVersion: document.getElementById("env-pi-version")?.value || "",
      intent: document.getElementById("env-intent")?.value || "",
      mockCamera: document.getElementById("env-mock-camera")?.value || "false",
    },
    preset: document.getElementById("preset-select")?.value || "custom",
    fields: collectSetupConfig(),
  };

  localStorage.setItem(setupWizard.storageKey, JSON.stringify(payload));
}

/**
 * Apply stored wizard state to form inputs.
 *
 * Restores environment selections, preset, and form field values from localStorage.
 * Safe-guards against missing IDs and invalid objects.
 *
 * @returns {void}
 */
function applyStoredWizardState() {
  const stored = getWizardStateFromStorage();
  if (!stored || typeof stored !== "object") return;

  const env = stored.environment || {};
  if (document.getElementById("env-pi-version")) {
    document.getElementById("env-pi-version").value = env.piVersion || "";
  }
  if (document.getElementById("env-intent")) {
    document.getElementById("env-intent").value = env.intent || "";
  }
  if (document.getElementById("env-mock-camera")) {
    document.getElementById("env-mock-camera").value = env.mockCamera || "false";
  }

  if (stored.preset && document.getElementById("preset-select")) {
    document.getElementById("preset-select").value = stored.preset;
  }

  applyConfigToForm(stored.fields || {});

  setupWizard.expertMode = Boolean(stored.expertMode);
  const expertToggle = document.getElementById("expert-mode-toggle");
  if (expertToggle) expertToggle.checked = setupWizard.expertMode;

  if (stored.currentStep && setupWizard.steps.includes(stored.currentStep)) {
    setupWizard.currentStep = stored.currentStep;
  }
}

/**
 * Collect setup wizard configuration from form inputs.
 *
 * @returns {Object} Configuration object with resolution, fps, quality settings.
 */
function collectSetupConfig() {
  return {
    resolution: document.getElementById("setup-resolution")?.value || "",
    fps: parseInt(document.getElementById("setup-fps")?.value || "0", 10) || 0,
    jpeg_quality: parseInt(document.getElementById("setup-jpeg-quality")?.value || "90", 10) || 90,
    max_connections:
      parseInt(document.getElementById("setup-max-connections")?.value || "10", 10) || 10,
    target_fps: document.getElementById("setup-target-fps")?.value
      ? parseInt(document.getElementById("setup-target-fps")?.value, 10)
      : null,
    pi3_profile: document.getElementById("setup-pi3-profile")?.value === "true",
    cors_origins: document.getElementById("setup-cors-origins")?.value || "",
    mock_camera: document.getElementById("setup-mock-camera")?.value === "true",
    auth_token: document.getElementById("setup-auth-token")?.value || "",
  };
}

/**
 * Apply configuration values to setup form inputs.
 *
 * @param {Object} config - Configuration object with setup values.
 * @returns {void}
 */
function applyConfigToForm(config) {
  if (!config || typeof config !== "object") return;

  const setValue = (id, value) => {
    const el = document.getElementById(id);
    if (el !== null && el !== undefined && value !== undefined && value !== null) {
      el.value = value;
    }
  };

  setValue("setup-resolution", config.resolution);
  setValue("setup-fps", config.fps);
  setValue("setup-jpeg-quality", config.jpeg_quality);
  setValue("setup-max-connections", config.max_connections);
  setValue("setup-target-fps", config.target_fps ?? "");
  setValue("setup-pi3-profile", config.pi3_profile ? "true" : "false");
  setValue("setup-cors-origins", config.cors_origins || "");
  setValue("setup-mock-camera", config.mock_camera ? "true" : "false");
  if (Object.prototype.hasOwnProperty.call(config, "auth_token")) {
    setValue("setup-auth-token", config.auth_token || "");
  }
}

/**
 * Infer recommended setup preset from environment selector values.
 *
 * @returns {string} Preset name ("pi3_low_power", "pi5_high_quality", or "custom").
 */
function inferPresetFromEnvironment() {
  const piVersion = document.getElementById("env-pi-version")?.value;
  const intent = document.getElementById("env-intent")?.value;

  if (piVersion === "pi3") return "pi3_low_power";
  if (piVersion === "pi5" || intent === "management") return "pi5_high_quality";
  return "custom";
}

/**
 * Apply a preset configuration to the setup form.
 *
 * @param {string} preset - Preset name ("pi3_low_power", "pi5_high_quality", "custom").
 * @returns {void}
 */
function applyPresetToForm(preset) {
  const envMockCamera = document.getElementById("env-mock-camera")?.value || "false";

  if (preset === "pi3_low_power") {
    applyConfigToForm({
      resolution: "640x480",
      fps: 12,
      jpeg_quality: 75,
      max_connections: 3,
      target_fps: 12,
      pi3_profile: true,
      mock_camera: envMockCamera === "true",
    });
  } else if (preset === "pi5_high_quality") {
    applyConfigToForm({
      resolution: "1280x720",
      fps: 24,
      jpeg_quality: 90,
      max_connections: 10,
      target_fps: 24,
      pi3_profile: false,
      mock_camera: envMockCamera === "true",
    });
  } else {
    applyConfigToForm({
      mock_camera: envMockCamera === "true",
    });
  }
}

function getStepIndex(step) {
  return setupWizard.steps.indexOf(step);
}

/**
 * Navigate to a wizard step, updating UI and saving state.
 *
 * @param {string} step - Step name (e.g., "environment", "preset", "review").
 * @returns {void}
 */
function setWizardStep(step) {
  if (!setupWizard.steps.includes(step)) return;
  setupWizard.currentStep = step;

  document.querySelectorAll(".wizard-step-panel").forEach((panel) => {
    panel.classList.toggle("hidden", panel.getAttribute("data-step-panel") !== step);
  });

  document.querySelectorAll(".wizard-step").forEach((stepButton) => {
    const isActive = stepButton.getAttribute("data-step") === step;
    stepButton.classList.toggle("is-active", isActive);
  });

  updateWizardCompletion();
  updateWizardNavigation();
  updateReviewSummary();
  saveWizardState();
}

/**
 * Validate wizard step form inputs.
 *
 * @param {string} step - Step name to validate ("environment", "preset", "review", etc.).
 * @returns {boolean} True if step is valid or expert mode enabled; false if validation required but failed.
 */
function validateStep(step) {
  if (setupWizard.expertMode) return true;

  if (step === "environment") {
    return (
      Boolean(document.getElementById("env-pi-version")?.value) &&
      Boolean(document.getElementById("env-intent")?.value)
    );
  }

  if (step === "preset") {
    return Boolean(document.getElementById("preset-select")?.value);
  }

  if (step === "review") {
    const resolution = document.getElementById("setup-resolution")?.value || "";
    const fps = Number.parseInt(document.getElementById("setup-fps")?.value || "", 10);
    return /^\d+x\d+$/i.test(resolution) && Number.isInteger(fps) && fps >= 1 && fps <= 120;
  }

  return true;
}

/**
 * Update wizard step completion indicators (✓, !, ○).
 *
 * Marks steps as valid (✓), invalid if past (!) or pending (○) based on validation.
 *
 * @returns {void}
 */
function updateWizardCompletion() {
  setupWizard.steps.forEach((step) => {
    const statusEl = document.querySelector(`[data-step-status="${step}"]`);
    if (!statusEl) return;

    const stepValid = validateStep(step);
    const stepIndex = getStepIndex(step);
    const currentIndex = getStepIndex(setupWizard.currentStep);

    if (stepValid) {
      statusEl.textContent = "✓";
    } else if (stepIndex <= currentIndex) {
      statusEl.textContent = "!";
    } else {
      statusEl.textContent = "○";
    }
  });
}

/**
 * Update wizard navigation buttons (Previous/Next) state.
 *
 * Disables Previous at first step, enables Next only if current step validates.
 * Changes "Next" to "Done" at final step.
 *
 * @returns {void}
 */
function updateWizardNavigation() {
  const currentIndex = getStepIndex(setupWizard.currentStep);
  const prevBtn = document.getElementById("setup-prev-btn");
  const nextBtn = document.getElementById("setup-next-btn");

  if (prevBtn) prevBtn.disabled = currentIndex <= 0;

  if (nextBtn) {
    if (currentIndex >= setupWizard.steps.length - 1) {
      nextBtn.disabled = true;
      nextBtn.textContent = "Done";
    } else {
      nextBtn.disabled = !validateStep(setupWizard.currentStep);
      nextBtn.textContent = "Next";
    }
  }
}

function escapeHtml(unsafe) {
  return String(unsafe)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

/**
 * Update preset recommendation based on environment selection.
 *
 * Displays recommended preset and auto-selects if user hasn't chosen one.
 * Applies preset configuration to form.
 *
 * @returns {void}
 */
function updatePresetRecommendation() {
  const recommendedPreset = inferPresetFromEnvironment();
  const recommendation = document.getElementById("preset-recommendation");
  if (recommendation) {
    recommendation.textContent = `Recommended from environment answers: ${recommendedPreset}`;
  }

  const presetSelect = document.getElementById("preset-select");
  if (presetSelect && (!presetSelect.value || presetSelect.value === "custom")) {
    presetSelect.value = recommendedPreset;
    applyPresetToForm(recommendedPreset);
  }
}

/**
 * Update review summary panel with selected configuration values.
 *
 * Displays environment, preset, resolution, FPS selected by user.
 *
 * @returns {void}
 */
function updateReviewSummary() {
  const summary = document.getElementById("review-summary");
  if (!summary) return;

  const piVersion = document.getElementById("env-pi-version")?.value || "not selected";
  const intent = document.getElementById("env-intent")?.value || "not selected";
  const preset = document.getElementById("preset-select")?.value || "custom";
  const config = collectSetupConfig();

  summary.innerHTML = `<div class="instructions-header">🧾 Configuration summary</div>
    <ul class="instructions-list">
      <li><strong>Hardware:</strong> ${escapeHtml(piVersion)}</li>
      <li><strong>Intent:</strong> ${escapeHtml(intent)}</li>
      <li><strong>Preset:</strong> ${escapeHtml(preset)}</li>
      <li><strong>Resolution / FPS:</strong> ${escapeHtml(config.resolution || "--")} @ ${escapeHtml(config.fps || "--")}</li>
      <li><strong>Mock camera:</strong> ${config.mock_camera ? "Yes" : "No"}</li>
    </ul>`;
}

/**
 * Navigate to next setup wizard step if current step validates.
 *
 * Updates preset recommendation when leaving environment step.
 *
 * @returns {void}
 */
function onSetupNext() {
  if (!validateStep(setupWizard.currentStep)) return;

  if (setupWizard.currentStep === "environment") {
    updatePresetRecommendation();
  }

  const nextIndex = getStepIndex(setupWizard.currentStep) + 1;
  if (nextIndex < setupWizard.steps.length) {
    setWizardStep(setupWizard.steps[nextIndex]);
  }
}

/**
 * Navigate to previous setup wizard step.
 *
 * @returns {void}
 */
function onSetupPrevious() {
  const prevIndex = getStepIndex(setupWizard.currentStep) - 1;
  if (prevIndex >= 0) {
    setWizardStep(setupWizard.steps[prevIndex]);
  }
}

/**
 * Load setup tab data and initialize event listeners.
 *
 * Fetches setup templates from /api/setup/templates, initializes wizard UI,
 * restores saved form state, and displays device detection results.
 * Updates status indicator on success or error.
 *
 * @async
 * @returns {Promise<void>}
 * @throws {Error} If template fetch fails or response is not OK.
 */
async function loadSetupTab() {
  try {
    const setupPanel = state.elements.setupPanel;
    if (!setupPanel) return;

    const setupLoading = document.getElementById("setup-loading");
    if (setupLoading) setupLoading.classList.remove("hidden");

    const response = await fetch("/api/setup/templates");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const data = await response.json();
    state.setupFormState = data.current_config || {};
    state.setupDetectedDevices = data.detected_devices || {};

    updateSetupUI(data);
    applyStoredWizardState();
    updatePresetRecommendation();

    if (setupLoading) setupLoading.classList.add("hidden");

    if (!setupWizard.initialized) {
      attachSetupEventListeners();
      setupWizard.initialized = true;
    }

    setWizardStep(setupWizard.currentStep);

    const statusDot = document.getElementById("setup-status-indicator");
    const statusText = document.getElementById("setup-status-text");
    if (statusDot) statusDot.className = "setup-status-dot ready";
    if (statusText) statusText.textContent = "Setup ready";
  } catch (error) {
    console.error("Failed to load setup tab:", error);
    showSetupError(`Failed to load setup: ${error.message}`);
    const statusDot = document.getElementById("setup-status-indicator");
    const statusText = document.getElementById("setup-status-text");
    if (statusDot) statusDot.className = "setup-status-dot error";
    if (statusText) statusText.textContent = "Setup load failed";
  }
}

/**
 * Analyze device detection results and provide setup guidance.
 *
 * Examines /dev/video*, /dev/media*, /dev/dma_heap, /dev/vchiq availability.
 * Returns status summary with tone, guidance, and recommendations based on signals detected.
 * Adapts guidance for management vs webcam mode.
 *
 * @param {Object} [devices={}] - Devices object with video_devices, media_devices, etc.
 * @param {Object} [currentConfig={}] - Current configuration object with intent mode.
 * @returns {Object} Summary with status, tone, guidance, recommendations, device counts.
 */
function getDeviceDetectionSummary(devices = {}, currentConfig = {}) {
  const videoCount = devices.video_devices?.length || 0;
  const mediaCount = devices.media_devices?.length || 0;
  const dmaCount = devices.dma_heap_devices?.length || 0;
  const hasVchiq = Boolean(devices.vchiq_device);
  const cameraSignals = [videoCount > 0, mediaCount > 0, hasVchiq].filter(Boolean).length;
  const modeIntent = document.getElementById("env-intent")?.value || currentConfig.intent || "";
  const isManagementMode = modeIntent === "management";

  if (cameraSignals >= 2) {
    return {
      status: "Camera likely ready",
      tone: "detected",
      guidance: "Camera interfaces look available. You can proceed with real camera streaming.",
      recommendations: [
        "Enable the camera interface in raspi-config and reboot if the stream still fails.",
        "Keep /dev/vchiq and /dev/video* mounted into the container for hardware access.",
      ],
      isManagementMode,
      videoCount,
      mediaCount,
      dmaCount,
      hasVchiq,
    };
  }

  if (cameraSignals === 0) {
    return {
      status: "No camera detected",
      tone: isManagementMode ? "warning" : "error",
      guidance: isManagementMode
        ? "Management mode can run without a physical camera, but streaming features will remain unavailable until hardware is attached."
        : "No camera interfaces were found. Check host device mounts and camera interface settings.",
      recommendations: [
        "Verify /dev/vchiq exists on the host and is mounted into the container.",
        "For local development without hardware, set MOCK_CAMERA=true.",
        "If using Raspberry Pi, enable Camera in raspi-config and reboot.",
      ],
      isManagementMode,
      videoCount,
      mediaCount,
      dmaCount,
      hasVchiq,
    };
  }

  return {
    status: "Partial detection",
    tone: "warning",
    guidance: "Some camera signals were detected, but not all expected interfaces are present.",
    recommendations: [
      "Confirm /dev/vchiq and /dev/video* are both available to the container.",
      "Check camera ribbon seating and reboot if interfaces are intermittent.",
      "Use MOCK_CAMERA=true during development to continue testing setup flows.",
    ],
    isManagementMode,
    videoCount,
    mediaCount,
    dmaCount,
    hasVchiq,
  };
}

/**
 * Render device detection status display with checklist and recommendations.
 *
 * Creates visual checklist of camera device interfaces with pass/fail indicators.
 * Displays detection summary, guidance text, and recommended next steps.
 * Uses detectDeviceDetectionSummary() to determine status tone and content.
 *
 * @param {Object} [devices={}] - Devices object from device detection endpoint.
 * @param {Object} [currentConfig={}] - Current configuration object.
 * @returns {void}
 */
function renderDeviceStatus(devices = {}, currentConfig = {}) {
  const deviceStatus = document.getElementById("device-status");
  if (!deviceStatus) return;

  const summary = getDeviceDetectionSummary(devices, currentConfig);

  const checklistItems = [
    {
      label: "Video devices (/dev/video*)",
      passed: summary.videoCount > 0,
      detail: summary.videoCount > 0 ? devices.video_devices.join(", ") : "None",
    },
    {
      label: "Media devices (/dev/media*)",
      passed: summary.mediaCount > 0,
      detail: summary.mediaCount > 0 ? devices.media_devices.join(", ") : "None",
    },
    {
      label: "DMA heap",
      passed: summary.dmaCount > 0,
      detail: summary.dmaCount > 0 ? devices.dma_heap_devices.join(", ") : "None",
    },
    {
      label: "/dev/vchiq",
      passed: summary.hasVchiq,
      detail: summary.hasVchiq ? "Detected" : "Not detected",
    },
  ];

  const checklistHtml = checklistItems
    .map(
      (item) => `
        <li class="device-check-item ${item.passed ? "passed" : "missing"}">
          <span class="check-icon">${item.passed ? "✅" : "⚪"}</span>
          <span class="check-label">${escapeHtml(item.label)}</span>
          <span class="check-detail">${escapeHtml(item.detail)}</span>
        </li>`,
    )
    .join("");

  const recommendationsHtml = summary.recommendations
    .map((recommendation) => `<li>${escapeHtml(recommendation)}</li>`)
    .join("");

  const modeNote = summary.isManagementMode
    ? '<p class="device-mode-note">ℹ️ Management mode selected: camera-less operation can be expected.</p>'
    : "";

  deviceStatus.innerHTML = `
    <div class="device-status-summary">
      <strong>${escapeHtml(summary.status)}</strong>
      <p>${escapeHtml(summary.guidance)}</p>
      ${modeNote}
    </div>
    <ul class="device-checklist">
      ${checklistHtml}
    </ul>
    <div class="device-recommendations device-recommendations-${summary.tone}">
      <p class="device-recommendations-title">Recommended next steps</p>
      <ul>${recommendationsHtml}</ul>
    </div>
  `;

  deviceStatus.className = `device-status ${summary.tone}`;
}

/**
 * Re-scan Raspberry Pi hardware devices and update UI.
 *
 * Queries /api/setup/templates for device detection, updates device status display,
 * disables button during scan operation, re-enables on completion or error.
 *
 * @async
 * @returns {Promise<void>}
 * @throws {Error} If device template fetch fails.
 */
async function rescanSetupDevices() {
  const rescanBtn = document.getElementById("rescan-devices-btn");
  if (rescanBtn) {
    rescanBtn.disabled = true;
    rescanBtn.textContent = "Scanning...";
  }

  try {
    const response = await fetch("/api/setup/templates");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const data = await response.json();
    state.setupDetectedDevices = data.detected_devices || {};
    state.setupFormState = data.current_config || state.setupFormState;
    renderDeviceStatus(state.setupDetectedDevices, state.setupFormState);
  } catch (error) {
    console.error("Failed to rescan devices:", error);
    showSetupError(`Failed to re-scan devices: ${error.message}`);
  } finally {
    if (rescanBtn) {
      rescanBtn.disabled = false;
      rescanBtn.textContent = "Re-scan devices";
    }
  }
}

/**
 * Update setup UI from template data.
 *
 * Renders device status, applies current configuration to form fields, updates mock camera setting.
 * Bridges between API response and UI form state.
 *
 * @param {Object} data - Setup templates data with detected_devices and current_config.
 * @returns {void}
 */
function updateSetupUI(data) {
  state.setupDetectedDevices = data.detected_devices || state.setupDetectedDevices || {};
  renderDeviceStatus(state.setupDetectedDevices, data.current_config || {});

  applyConfigToForm(data.current_config || {});

  if (data.current_config?.mock_camera !== undefined) {
    document.getElementById("env-mock-camera").value = data.current_config.mock_camera
      ? "true"
      : "false";
  }
}

function attachSetupEventListeners() {
  const presetSelect = document.getElementById("preset-select");
  if (presetSelect) {
    presetSelect.addEventListener("change", (event) => {
      onPresetChange(event);
      updateReviewSummary();
      saveWizardState();
    });
  }

  const generateBtn = document.getElementById("generate-btn");
  if (generateBtn) {
    generateBtn.addEventListener("click", onGenerateClick);
  }

  const expertToggle = document.getElementById("expert-mode-toggle");
  if (expertToggle) {
    expertToggle.addEventListener("change", (event) => {
      setupWizard.expertMode = event.target.checked;
      const advancedPanel = document.getElementById("advanced-review-panel");
      if (advancedPanel) advancedPanel.open = setupWizard.expertMode;
      updateWizardNavigation();
      updateWizardCompletion();
      saveWizardState();
    });
  }

  const nextBtn = document.getElementById("setup-next-btn");
  if (nextBtn) nextBtn.addEventListener("click", onSetupNext);

  const prevBtn = document.getElementById("setup-prev-btn");
  if (prevBtn) prevBtn.addEventListener("click", onSetupPrevious);

  const rescanBtn = document.getElementById("rescan-devices-btn");
  if (rescanBtn) rescanBtn.addEventListener("click", rescanSetupDevices);

  document.querySelectorAll(".wizard-step").forEach((btn) => {
    btn.addEventListener("click", () => {
      const requestedStep = btn.getAttribute("data-step");
      const requestedIndex = getStepIndex(requestedStep);
      const currentIndex = getStepIndex(setupWizard.currentStep);
      if (requestedIndex <= currentIndex || validateStep(setupWizard.currentStep)) {
        setWizardStep(requestedStep);
      }
    });
  });

  document.querySelectorAll(".output-copy-btn").forEach((btn) => {
    btn.addEventListener("click", function () {
      const targetId = this.getAttribute("data-target");
      copyToClipboard(targetId, this);
    });
  });

  ["env-pi-version", "env-intent", "env-mock-camera"].forEach((id) => {
    const field = document.getElementById(id);
    if (!field) return;
    field.addEventListener("change", () => {
      if (id === "env-mock-camera") {
        const mockCameraField = document.getElementById("setup-mock-camera");
        if (mockCameraField) mockCameraField.value = field.value;
      }
      if (id === "env-intent") {
        renderDeviceStatus(state.setupDetectedDevices || {}, state.setupFormState || {});
      }
      updatePresetRecommendation();
      validateSetupForm();
      saveWizardState();
    });
  });

  document.querySelectorAll("[data-field]").forEach((field) => {
    field.addEventListener("input", () => {
      validateSetupForm();
      updateReviewSummary();
      saveWizardState();
    });
    field.addEventListener("change", () => {
      validateSetupForm();
      updateReviewSummary();
      saveWizardState();
    });
  });
}

function onPresetChange(event) {
  const preset = event.target.value;
  applyPresetToForm(preset);
  validateSetupForm();
}

/**
 * Validate setup form field values.
 *
 * Validates resolution format (WIDTHxHEIGHT) and FPS range (0-120).
 * Updates wizard navigation and completion state.
 * Logs warnings to console for invalid values.
 *
 * @returns {void}
 */
function validateSetupForm() {
  const resolution = document.getElementById("setup-resolution")?.value || "";
  const fps = document.getElementById("setup-fps")?.value || "";

  if (resolution && !/^\d+x\d+$/i.test(resolution)) {
    console.warn("Invalid resolution format. Use WIDTHxHEIGHT (e.g., 640x480)");
  }

  if (fps && (isNaN(fps) || parseInt(fps, 10) < 0 || parseInt(fps, 10) > 120)) {
    console.warn("FPS must be between 0 and 120");
  }

  updateWizardNavigation();
  updateWizardCompletion();
}

/**
 * Generate and apply configuration from setup wizard.
 *
 * Validates form, collects configuration, posts to /api/setup/validate and /api/setup/generate,
 * displays results in modal, saves state, and updates main config panel on success.
 *
 * @async
 * @returns {Promise<void>}
 * @throws {Error} If validation or generation fails.
 */
async function onGenerateClick() {
  try {
    validateSetupForm();
    const config = collectSetupConfig();

    const validateResponse = await fetch("/api/setup/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });

    if (!validateResponse.ok) {
      const errorData = await validateResponse.json();
      throw new Error(errorData.error?.message || "Validation failed");
    }

    const validationResult = await validateResponse.json();
    if (!validationResult.valid && validationResult.errors?.length > 0) {
      showSetupError(`Validation errors: ${validationResult.errors.join(", ")}`);
      return;
    }

    const generateResponse = await fetch("/api/setup/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });

    if (!generateResponse.ok) {
      const errorData = await generateResponse.json();
      throw new Error(errorData.error?.message || "Generation failed");
    }

    const result = await generateResponse.json();

    const dockerComposeOutput = document.getElementById("docker-compose-output");
    if (dockerComposeOutput) dockerComposeOutput.value = result.docker_compose_yaml || "";

    const envOutput = document.getElementById("env-output");
    if (envOutput) envOutput.value = result.env_content || "";

    showSetupSuccess("Configuration generated successfully!");
    saveWizardState();
  } catch (error) {
    console.error("Generation failed:", error);
    showSetupError(`Generation failed: ${error.message}`);
  }
}

/**
 * Copy textarea content to clipboard
 */
function copyToClipboard(targetId, buttonElement) {
  const textarea = document.getElementById(targetId);
  if (!textarea) return;

  textarea.select();
  document.execCommand("copy");

  // Provide visual feedback
  const originalText = buttonElement.textContent;
  buttonElement.textContent = "✓ Copied!";
  buttonElement.classList.add("copied");

  setTimeout(() => {
    buttonElement.textContent = originalText;
    buttonElement.classList.remove("copied");
  }, 2000);
}

/**
 * Show setup error alert with message.
 *
 * Displays error message in setup error alert element.
 *
 * @param {string} message - Error message to display.
 * @returns {void}
 */
function showSetupError(message) {
  const errorAlert = document.getElementById("setup-error-alert");
  const errorMessage = document.getElementById("setup-error-message");

  if (errorAlert && errorMessage) {
    errorMessage.textContent = message;
    errorAlert.classList.remove("hidden");
  }
}

/**
 * Show setup success alert with message.
 *
 * Displays success message in setup success alert element.
 *
 * @param {string} message - Success message to display.
 * @returns {void}
 */
function showSetupSuccess(message) {
  const successAlert = document.getElementById("setup-success-alert");
  const successMessage = document.getElementById("setup-success-message");

  if (successAlert && successMessage) {
    successMessage.textContent = message;
    successAlert.classList.remove("hidden");

    setTimeout(() => {
      successAlert.classList.add("hidden");
    }, 3000);
  }
}

document.addEventListener("DOMContentLoaded", init);
