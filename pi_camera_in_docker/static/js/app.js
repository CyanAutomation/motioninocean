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
  configInitialLoadPending: false,
  configLoadingDelayTimer: null,
  configLoadingVisible: false,
  setupInitialLoadPending: false,
  setupLoadingDelayTimer: null,
  setupLoadingVisible: false,
  setupFormState: {},
  elements: {
    videoStream: null,
    statsPanel: null,
    configPanel: null,
    setupPanel: null,
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
  state.elements.setupPanel = document.getElementById("setup-panel");
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
  const wasSetupTab = state.currentTab === "setup";
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
  const setupPanel = state.elements.setupPanel;

  if (tabName === "main") {
    if (mainSection) mainSection.classList.remove("hidden");
    if (statsPanel) statsPanel.classList.remove("hidden");
    if (configPanel) configPanel.classList.add("hidden");
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
    if (setupPanel) setupPanel.classList.add("hidden");

    // Stop stats updates and start config refresh/timestamp updates
    stopStatsUpdate();

    if (!wasConfigTab) {
      state.configInitialLoadPending = true;
      updateConfig().catch((error) => console.error("Config update failed:", error));
      startConfigPolling();
    }
  } else if (tabName === "setup") {
    if (mainSection) mainSection.classList.add("hidden");
    if (statsPanel) statsPanel.classList.add("hidden");
    if (configPanel) configPanel.classList.add("hidden");
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
  const configValues = document.querySelectorAll('[data-config-value="true"]');
  configValues.forEach((el) => {
    el.textContent = "--";
    el.className = "config-value";
  });
}

/* ==========================================
   Setup Tab Functions
   ========================================== */

/**
 * Load setup tab data and initialize event listeners
 */
async function loadSetupTab() {
  try {
    const setupPanel = state.elements.setupPanel;
    if (!setupPanel) return;

    // Show loading state
    const setupLoading = document.getElementById("setup-loading");
    if (setupLoading) setupLoading.classList.remove("hidden");

    // Fetch setup templates
    const response = await fetch("/api/setup/templates");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const data = await response.json();
    state.setupFormState = data.current_config || {};

    // Update UI with fetched data
    updateSetupUI(data);

    // Hide loading state
    if (setupLoading) setupLoading.classList.add("hidden");

    // Attach event listeners
    attachSetupEventListeners();

    // Update status
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
 * Update setup UI with templates and current config
 */
function updateSetupUI(data) {
  // Populate device status
  const deviceStatus = document.getElementById("device-status");
  if (deviceStatus && data.detected_devices) {
    const devices = data.detected_devices;
    if (Object.keys(devices).length > 0) {
      let deviceInfo = "<strong>Detected Camera Devices:</strong><br>";
      if (devices.video_devices?.length)
        deviceInfo += `📹 Video: ${devices.video_devices.join(", ")}<br>`;
      if (devices.media_devices?.length)
        deviceInfo += `📡 Media: ${devices.media_devices.join(", ")}<br>`;
      if (devices.dma_heap_devices?.length)
        deviceInfo += `💾 DMA: ${devices.dma_heap_devices.join(", ")}<br>`;
      if (devices.vchiq_device) deviceInfo += `🔧 VCHIQ: Detected<br>`;
      deviceStatus.innerHTML = deviceInfo;
      deviceStatus.className = "device-status detected";
    } else {
      deviceStatus.textContent = "No camera devices detected (may be normal on non-Pi systems)";
      deviceStatus.className = "device-status";
    }
  }

  // Populate form fields with current config
  if (data.current_config) {
    const config = data.current_config;
    const resolution = document.getElementById("setup-resolution");
    if (resolution && config.resolution) resolution.value = config.resolution;

    const fps = document.getElementById("setup-fps");
    if (fps && config.fps !== undefined) fps.value = config.fps;

    const jpegQuality = document.getElementById("setup-jpeg-quality");
    if (jpegQuality && config.jpeg_quality !== undefined) jpegQuality.value = config.jpeg_quality;

    const maxConnections = document.getElementById("setup-max-connections");
    if (maxConnections && config.max_connections !== undefined)
      maxConnections.value = config.max_connections;

    const targetFps = document.getElementById("setup-target-fps");
    if (targetFps && config.target_fps !== undefined) targetFps.value = config.target_fps || "";

    const pi3Profile = document.getElementById("setup-pi3-profile");
    if (pi3Profile && config.pi3_profile !== undefined)
      pi3Profile.value = config.pi3_profile ? "true" : "false";

    const corsOrigins = document.getElementById("setup-cors-origins");
    if (corsOrigins && config.cors_origins !== undefined)
      corsOrigins.value = config.cors_origins || "";

    const mockCamera = document.getElementById("setup-mock-camera");
    if (mockCamera && config.mock_camera !== undefined)
      mockCamera.value = config.mock_camera ? "true" : "false";
  }
}

/**
 * Attach event listeners to setup form elements
 */
function attachSetupEventListeners() {
  // Preset selector
  const presetSelect = document.getElementById("preset-select");
  if (presetSelect) {
    presetSelect.addEventListener("change", onPresetChange);
  }

  // Advanced toggle
  const advancedToggleBtn = document.getElementById("advanced-toggle-btn");
  if (advancedToggleBtn) {
    advancedToggleBtn.addEventListener("click", toggleAdvanced);
  }

  // Generate button
  const generateBtn = document.getElementById("generate-btn");
  if (generateBtn) {
    generateBtn.addEventListener("click", onGenerateClick);
  }

  // Copy buttons
  document.querySelectorAll(".output-copy-btn").forEach((btn) => {
    btn.addEventListener("click", function () {
      const targetId = this.getAttribute("data-target");
      copyToClipboard(targetId, this);
    });
  });

  // Form field changes for real-time validation
  const formFields = document.querySelectorAll("[data-field]");
  formFields.forEach((field) => {
    field.addEventListener("change", validateSetupForm);
    field.addEventListener("blur", validateSetupForm);
  });
}

/**
 * Handle preset selection change
 */
function onPresetChange(event) {
  const preset = event.target.value;
  const config = state.setupFormState;

  if (preset === "pi3_low_power") {
    document.getElementById("setup-resolution").value = "640x480";
    document.getElementById("setup-fps").value = 12;
    document.getElementById("setup-jpeg-quality").value = 75;
    document.getElementById("setup-max-connections").value = 3;
    document.getElementById("setup-pi3-profile").value = "true";
    document.getElementById("setup-target-fps").value = 12;
  } else if (preset === "pi5_high_quality") {
    document.getElementById("setup-resolution").value = "1280x720";
    document.getElementById("setup-fps").value = 24;
    document.getElementById("setup-jpeg-quality").value = 90;
    document.getElementById("setup-max-connections").value = 10;
    document.getElementById("setup-pi3-profile").value = "false";
    document.getElementById("setup-target-fps").value = 24;
  } else if (preset === "custom") {
    // Already set from current config in updateSetupUI
  }

  validateSetupForm();
}

/**
 * Toggle advanced settings visibility
 */
function toggleAdvanced(event) {
  if (event) event.preventDefault();

  const btn = document.getElementById("advanced-toggle-btn");
  const advancedContent = document.getElementById("advanced-content");

  if (btn && advancedContent) {
    const isExpanded = btn.classList.contains("expanded");

    if (isExpanded) {
      btn.classList.remove("expanded");
      advancedContent.classList.remove("visible");
      advancedContent.classList.add("hidden");
    } else {
      btn.classList.add("expanded");
      advancedContent.classList.add("visible");
      advancedContent.classList.remove("hidden");
    }
  }
}

/**
 * Validate setup form fields
 */
function validateSetupForm() {
  const resolution = document.getElementById("setup-resolution")?.value || "";
  const fps = document.getElementById("setup-fps")?.value || "";

  // Basic validation: resolution format
  if (resolution && !/^\d+x\d+$/i.test(resolution)) {
    console.warn("Invalid resolution format. Use WIDTHxHEIGHT (e.g., 640x480)");
  }

  // FPS validation
  if (fps && (isNaN(fps) || parseInt(fps) < 0 || parseInt(fps) > 120)) {
    console.warn("FPS must be between 0 and 120");
  }
}

/**
 * Handle Generate button click
 */
async function onGenerateClick() {
  try {
    // Validate form
    validateSetupForm();

    // Collect form values
    const config = {
      resolution: document.getElementById("setup-resolution")?.value || "",
      fps: parseInt(document.getElementById("setup-fps")?.value || "0") || 0,
      jpeg_quality: parseInt(document.getElementById("setup-jpeg-quality")?.value || "90") || 90,
      max_connections:
        parseInt(document.getElementById("setup-max-connections")?.value || "10") || 10,
      target_fps: document.getElementById("setup-target-fps")?.value
        ? parseInt(document.getElementById("setup-target-fps")?.value)
        : null,
      pi3_profile: document.getElementById("setup-pi3-profile")?.value === "true",
      cors_origins: document.getElementById("setup-cors-origins")?.value || "",
      mock_camera: document.getElementById("setup-mock-camera")?.value === "true",
      auth_token: document.getElementById("setup-auth-token")?.value || "",
    };

    // Validate via API
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

    // Generate files
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

    // Populate output textareas
    const dockerComposeOutput = document.getElementById("docker-compose-output");
    if (dockerComposeOutput) dockerComposeOutput.value = result.docker_compose_yaml || "";

    const envOutput = document.getElementById("env-output");
    if (envOutput) envOutput.value = result.env_content || "";

    showSetupSuccess("Configuration generated successfully!");
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
 * Show setup error alert
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
 * Show setup success alert
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
