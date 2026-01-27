/**
 * motion-in-ocean - Camera Stream Application
 * Real-time stats, fullscreen, refresh, and connection monitoring
 */

const state = {
  updateInterval: null,
  updateFrequency: 2000,
  connectionTimeout: null,
  isConnected: false,
  statsCollapsed: false,
  statsInFlight: false,
  elements: {
    videoStream: null,
    statsPanel: null,
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
    edgeDetectionValue: null,
    lastUpdated: null
  }
};

/**
 * Initialize the application
 */
function init() {
  cacheElements();
  attachHandlers();
  startStatsUpdate();
  updateStats().catch(error => console.error('Initial stats update failed:', error));

  console.log('🎥 motion-in-ocean camera stream initialized');
}

/**
 * Cache DOM elements for performance
 */
function cacheElements() {
  state.elements.videoStream = document.getElementById('video-stream');
  state.elements.statsPanel = document.getElementById('stats-panel');
  state.elements.toggleStatsBtn = document.getElementById('toggle-stats-btn');
  state.elements.refreshBtn = document.getElementById('refresh-btn');
  state.elements.fullscreenBtn = document.getElementById('fullscreen-btn');
  state.elements.statusIndicator = document.getElementById('status-indicator');
  state.elements.statusText = document.getElementById('status-text');

  state.elements.fpsValue = document.getElementById('fps-value');
  state.elements.uptimeValue = document.getElementById('uptime-value');
  state.elements.framesValue = document.getElementById('frames-value');
  state.elements.lastFrameAgeValue = document.getElementById('last-frame-age-value');
  state.elements.maxFrameAgeValue = document.getElementById('max-frame-age-value');
  state.elements.resolutionValue = document.getElementById('resolution-value');
  state.elements.edgeDetectionValue = document.getElementById('edge-detection-value');
  state.elements.lastUpdated = document.getElementById('last-updated');
}

/**
 * Attach event listeners
 */
function attachHandlers() {
  if (state.elements.toggleStatsBtn) {
    state.elements.toggleStatsBtn.addEventListener('click', toggleStats);
  }

  if (state.elements.refreshBtn) {
    state.elements.refreshBtn.addEventListener('click', refreshStream);
  }

  if (state.elements.fullscreenBtn) {
    state.elements.fullscreenBtn.addEventListener('click', toggleFullscreen);
  }

  if (state.elements.videoStream) {
    state.elements.videoStream.addEventListener('load', onStreamLoad);
    state.elements.videoStream.addEventListener('error', onStreamError);
  }

  document.addEventListener('fullscreenchange', onFullscreenChange);
  document.addEventListener('webkitfullscreenchange', onFullscreenChange);
  document.addEventListener('mozfullscreenchange', onFullscreenChange);
  document.addEventListener('MSFullscreenChange', onFullscreenChange);

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      stopStatsUpdate();
    } else {
      startStatsUpdate();
      updateStats().catch(error => console.error('Stats update failed:', error));
    }
  });
}

/**
 * Fetch and update stats from /metrics endpoint
 */
async function updateStats() {
  if (state.statsInFlight) return;
  
  try {
    state.statsInFlight = true;
  try {
    const data = await fetchMetrics();
    renderMetrics(data);
  } catch (error) {
    console.error('Failed to fetch stats:', error);
    setConnectionStatus('disconnected', 'Disconnected');

    if (state.elements.fpsValue) {
      state.elements.fpsValue.textContent = '--';
    }

    if (state.elements.uptimeValue) {
      state.elements.uptimeValue.textContent = '--';
    }

    if (state.elements.framesValue) {
      state.elements.framesValue.textContent = '--';
    }

    if (state.elements.lastFrameAgeValue) {
      state.elements.lastFrameAgeValue.textContent = '--';
    }

    if (state.elements.maxFrameAgeValue) {
      state.elements.maxFrameAgeValue.textContent = '--';
    }

    if (state.elements.resolutionValue) {
      state.elements.resolutionValue.textContent = '--';
    }

    if (state.elements.edgeDetectionValue) {
      state.elements.edgeDetectionValue.textContent = '--';
      state.elements.edgeDetectionValue.className = 'stat-badge';
    }

    if (state.elements.lastUpdated) {
      state.elements.lastUpdated.textContent = '--';
    }

    return;
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
    state.elements.statsPanel.classList.toggle('collapsed', state.statsCollapsed);
  }

  if (state.elements.toggleStatsBtn) {
    state.elements.toggleStatsBtn.textContent = state.statsCollapsed ? '▼' : '▲';
  }
}

/**
 * Refresh video stream
 */
function refreshStream() {
  if (!state.elements.videoStream) return;

  const streamUrl = state.elements.videoStream.src.split('?')[0];
  state.elements.videoStream.src = `${streamUrl}?t=${Date.now()}`;

  if (state.elements.refreshBtn) {
    state.elements.refreshBtn.style.transform = 'rotate(360deg)';
    setTimeout(() => {
      state.elements.refreshBtn.style.transform = '';
    }, 300);
  }
}

/**
 * Toggle fullscreen mode
 */
function toggleFullscreen() {
  const container = document.querySelector('.video-container');
  if (!container) return;

  if (!document.fullscreenElement &&
      !document.webkitFullscreenElement &&
      !document.mozFullScreenElement &&
      !document.msFullscreenElement) {
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
  const isFullscreen = !!(document.fullscreenElement ||
                         document.webkitFullscreenElement ||
                         document.mozFullScreenElement ||
                         document.msFullscreenElement);

  if (state.elements.fullscreenBtn) {
    const btnText = state.elements.fullscreenBtn.querySelector('.control-btn-text');
    if (btnText) {
      btnText.textContent = isFullscreen ? 'Exit Fullscreen' : 'Fullscreen';
    }
    const btnIcon = state.elements.fullscreenBtn.querySelector('.control-btn-icon');
    if (btnIcon) {
      btnIcon.textContent = isFullscreen ? '⛶' : '⛶';
    }
  }
}

/**
 * Handle stream load event
 */
function onStreamLoad() {
  hideLoading();
  setConnectionStatus('connected', 'Stream Connected');
}

/**
 * Handle stream error event
 */
function onStreamError() {
  console.error('Video stream error');
  setConnectionStatus('disconnected', 'Stream Error');
}

/**
 * Set connection status
 */
function setConnectionStatus(status, text) {
  state.isConnected = status === 'connected';

  if (state.elements.statusIndicator) {
    state.elements.statusIndicator.className = 'status-indicator';
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

  state.updateInterval = setInterval(() => {
    updateStats().catch(error => console.error('Stats update failed:', error));
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
 * Fetch stats from /metrics endpoint
 */
async function fetchMetrics() {
  const timeoutMs = 5000;
  const raceWithTimeout = (promise, timeout) => {
    let timeoutId;
    const timeoutPromise = new Promise((_, reject) => {
      timeoutId = setTimeout(() => {
        reject(new Error('Request timed out'));
      }, timeout);
    });

    return Promise.race([promise, timeoutPromise]).finally(() => {
      clearTimeout(timeoutId);
    });
  };

  const response = await raceWithTimeout(fetch('/metrics'), timeoutMs);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json();
}

/**
 * Render metrics data in the UI
 */
function renderMetrics(data) {
  if (!state.isConnected) {
    setConnectionStatus('connected', 'Connected');
  }

  if (state.elements.fpsValue) {
    state.elements.fpsValue.textContent = data.current_fps
      ? data.current_fps.toFixed(1)
      : '0.0';
  }

  if (state.elements.uptimeValue) {
    state.elements.uptimeValue.textContent = formatUptime(data.uptime_seconds);
  }

  if (state.elements.framesValue) {
    state.elements.framesValue.textContent = formatNumber(data.frames_captured);
  }

  if (state.elements.lastFrameAgeValue) {
    state.elements.lastFrameAgeValue.textContent = formatSeconds(
      data.last_frame_age_seconds
    );
  }

  if (state.elements.maxFrameAgeValue) {
    state.elements.maxFrameAgeValue.textContent = formatSeconds(
      data.max_frame_age_seconds
    );
  }

  if (state.elements.resolutionValue) {
    if (data.resolution && Array.isArray(data.resolution)) {
      state.elements.resolutionValue.textContent =
        `${data.resolution[0]} × ${data.resolution[1]}`;
    }
  }

  if (state.elements.edgeDetectionValue) {
    const badge = state.elements.edgeDetectionValue;
    badge.textContent = data.edge_detection ? 'Enabled' : 'Disabled';
    badge.className = 'stat-badge';
    badge.classList.add(data.edge_detection ? 'enabled' : 'disabled');
  }

  if (state.elements.lastUpdated) {
    const now = new Date();
    state.elements.lastUpdated.textContent =
      `Updated: ${now.toLocaleTimeString()}`;
  }
}

/**
 * Format uptime in human-readable format
 */
function formatUptime(seconds) {
  if (!seconds || seconds < 0) return '0s';

  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  const parts = [];
  if (days > 0) parts.push(`${days}d`);
  if (hours > 0) parts.push(`${hours}h`);
  if (minutes > 0) parts.push(`${minutes}m`);
  if (secs > 0 || parts.length === 0) parts.push(`${secs}s`);

  return parts.join(' ');
}

/**
 * Format large numbers with commas
 */
function formatNumber(num) {
  if (num === null || num === undefined) return '0';
  return num.toLocaleString();
}

/**
 * Format seconds with a consistent precision
 */
function formatSeconds(seconds) {
  if (seconds === null || seconds === undefined) return '--';
  if (Number.isNaN(seconds)) return '--';
  return `${Number(seconds).toFixed(2)}s`;
}

/**
 * Hide loading overlay
 */
function hideLoading() {
  const loadingOverlay = document.querySelector('.loading-overlay');
  if (loadingOverlay) {
    loadingOverlay.style.opacity = '0';
    setTimeout(() => {
      loadingOverlay.remove();
    }, 300);
  }
}

document.addEventListener('DOMContentLoaded', init);
