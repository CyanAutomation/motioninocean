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
  setupDetectedDevices: {},
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
    setConfigValue(
      "config-cors",
      typeof sc.cors_origins === "string" && sc.cors_origins.length > 0
        ? sc.cors_origins
        : "disabled",
    );
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

const setupWizard = {
  storageKey: "motioninocean.setupWizard.v1",
  steps: ["environment", "preset", "review", "generate"],
  currentStep: "environment",
  expertMode: false,
  initialized: false,
};

function getWizardStateFromStorage() {
  try {
    const raw = localStorage.getItem(setupWizard.storageKey);
    return raw ? JSON.parse(raw) : {};
  } catch (_error) {
    return {};
  }
}

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
  setValue("setup-auth-token", config.auth_token || "");
}

function inferPresetFromEnvironment() {
  const piVersion = document.getElementById("env-pi-version")?.value;
  const intent = document.getElementById("env-intent")?.value;

  if (piVersion === "pi3") return "pi3_low_power";
  if (piVersion === "pi5" || intent === "management") return "pi5_high_quality";
  return "custom";
}

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
    return /^\d+x\d+$/i.test(resolution) && Number.isInteger(fps) && fps >= 0 && fps <= 120;
  }

  return true;
}

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

function onSetupPrevious() {
  const prevIndex = getStepIndex(setupWizard.currentStep) - 1;
  if (prevIndex >= 0) {
    setWizardStep(setupWizard.steps[prevIndex]);
  }
}

/**
 * Load setup tab data and initialize event listeners
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
