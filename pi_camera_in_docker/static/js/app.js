/**
 * motion-in-ocean - Camera Stream Application
 * Real-time stats, fullscreen, refresh, and connection monitoring
 */

class CameraStreamApp {
  constructor() {
    this.updateInterval = null;
    this.updateFrequency = 2000; // Update every 2 seconds
    this.connectionTimeout = null;
    this.isConnected = false;
    this.statsCollapsed = false;
    this.statsInFlight = false;
    this.pollingPausedForRetry = false;
    
    // Retry/backoff configuration
    this.retryAttempts = 0;
    this.maxRetries = 5;
    this.baseDelay = 1000; // 1 second base delay
    this.maxDelay = 30000; // 30 seconds max delay
    this.retryTimeout = null;

    // Stream retry/backoff configuration
    this.streamRetryAttempts = 0;
    this.streamRetryTimeout = null;
    this.streamBaseDelay = 2000; // 2 seconds base delay for stream reloads
    
    // DOM elements
    this.elements = {
      videoStream: null,
      statsPanel: null,
      toggleStatsBtn: null,
      refreshBtn: null,
      fullscreenBtn: null,
      statusIndicator: null,
      statusText: null,
      // Stats elements
      fpsValue: null,
      uptimeValue: null,
      framesValue: null,
      lastFrameAgeValue: null,
      maxFrameAgeValue: null,
      resolutionValue: null,
      edgeDetectionValue: null,
      lastUpdated: null
    };
    
    this.init();
  }
  
  /**
   * Initialize the application
   */
  init() {
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.setup());
    } else {
      this.setup();
    }
  }
  
  /**
   * Setup application after DOM is ready
   */
  setup() {
    this.cacheElements();
    this.attachEventListeners();
    this.startStatsUpdate();
    this.checkConnection();
    
    // Initial stats fetch
    this.updateStats();
    
    console.log('🎥 motion-in-ocean camera stream initialized');
  }
  
  /**
   * Cache DOM elements for performance
   */
  cacheElements() {
    this.elements.videoStream = document.getElementById('video-stream');
    this.elements.statsPanel = document.getElementById('stats-panel');
    this.elements.toggleStatsBtn = document.getElementById('toggle-stats-btn');
    this.elements.refreshBtn = document.getElementById('refresh-btn');
    this.elements.fullscreenBtn = document.getElementById('fullscreen-btn');
    this.elements.statusIndicator = document.getElementById('status-indicator');
    this.elements.statusText = document.getElementById('status-text');
    
    // Stats elements
    this.elements.fpsValue = document.getElementById('fps-value');
    this.elements.uptimeValue = document.getElementById('uptime-value');
    this.elements.framesValue = document.getElementById('frames-value');
    this.elements.lastFrameAgeValue = document.getElementById('last-frame-age-value');
    this.elements.maxFrameAgeValue = document.getElementById('max-frame-age-value');
    this.elements.resolutionValue = document.getElementById('resolution-value');
    this.elements.edgeDetectionValue = document.getElementById('edge-detection-value');
    this.elements.lastUpdated = document.getElementById('last-updated');
  }
  
  /**
   * Attach event listeners
   */
  attachEventListeners() {
    // Toggle stats panel (mobile)
    if (this.elements.toggleStatsBtn) {
      this.elements.toggleStatsBtn.addEventListener('click', () => this.toggleStats());
    }
    
    // Refresh stream
    if (this.elements.refreshBtn) {
      this.elements.refreshBtn.addEventListener('click', () => this.refreshStream());
    }
    
    // Fullscreen toggle
    if (this.elements.fullscreenBtn) {
      this.elements.fullscreenBtn.addEventListener('click', () => this.toggleFullscreen());
    }
    
    // Video stream load/error events
    if (this.elements.videoStream) {
      this.elements.videoStream.addEventListener('load', () => this.onStreamLoad());
      this.elements.videoStream.addEventListener('error', () => this.onStreamError());
    }
    
    // Fullscreen change events
    document.addEventListener('fullscreenchange', () => this.onFullscreenChange());
    document.addEventListener('webkitfullscreenchange', () => this.onFullscreenChange());
    document.addEventListener('mozfullscreenchange', () => this.onFullscreenChange());
    document.addEventListener('MSFullscreenChange', () => this.onFullscreenChange());
    
    // Page visibility API - pause updates when tab is hidden
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        this.stopStatsUpdate();
      } else {
        this.startStatsUpdate();
        this.updateStats();
      }
    });
  }
  
  /**
   * Toggle stats panel visibility (mobile)
   */
  toggleStats() {
    this.statsCollapsed = !this.statsCollapsed;
    
    if (this.elements.statsPanel) {
      this.elements.statsPanel.classList.toggle('collapsed', this.statsCollapsed);
    }
    
    if (this.elements.toggleStatsBtn) {
      this.elements.toggleStatsBtn.textContent = this.statsCollapsed ? '▼' : '▲';
    }
  }
  
  /**
   * Refresh video stream
   */
  refreshStream() {
    if (!this.elements.videoStream) return;
    
    // Add timestamp to force reload
    const streamUrl = this.elements.videoStream.src.split('?')[0];
    this.elements.videoStream.src = `${streamUrl}?t=${Date.now()}`;
    
    // Visual feedback
    if (this.elements.refreshBtn) {
      this.elements.refreshBtn.style.transform = 'rotate(360deg)';
      setTimeout(() => {
        this.elements.refreshBtn.style.transform = '';
      }, 300);
    }
    
    this.setConnectionStatus('connecting', 'Reconnecting...');
  }
  
  /**
   * Toggle fullscreen mode
   */
  toggleFullscreen() {
    const container = document.querySelector('.video-container');
    if (!container) return;
    
    if (!document.fullscreenElement && 
        !document.webkitFullscreenElement && 
        !document.mozFullScreenElement && 
        !document.msFullscreenElement) {
      // Enter fullscreen
      if (container.requestFullscreen) {
        container.requestFullscreen();
      } else if (container.webkitRequestFullscreen) {
        container.webkitRequestFullscreen();
      } else if (container.mozRequestFullScreen) {
        container.mozRequestFullScreen();
      } else if (container.msRequestFullscreen) {
        container.msRequestFullscreen();
      }
    } else {
      // Exit fullscreen
      if (document.exitFullscreen) {
        document.exitFullscreen();
      } else if (document.webkitExitFullscreen) {
        document.webkitExitFullscreen();
      } else if (document.mozCancelFullScreen) {
        document.mozCancelFullScreen();
      } else if (document.msExitFullscreen) {
        document.msExitFullscreen();
      }
    }
  }
  
  /**
   * Handle fullscreen change events
   */
  onFullscreenChange() {
    const isFullscreen = !!(document.fullscreenElement || 
                           document.webkitFullscreenElement || 
                           document.mozFullScreenElement || 
                           document.msFullscreenElement);
    
    if (this.elements.fullscreenBtn) {
      const btnText = this.elements.fullscreenBtn.querySelector('.control-btn-text');
      if (btnText) {
        btnText.textContent = isFullscreen ? 'Exit Fullscreen' : 'Fullscreen';
      }
      const btnIcon = this.elements.fullscreenBtn.querySelector('.control-btn-icon');
      if (btnIcon) {
        btnIcon.textContent = isFullscreen ? '⛶' : '⛶';
      }
    }
  }
  
  /**
   * Handle stream load event
   */
  onStreamLoad() {
    this.setConnectionStatus('connected', 'Connected');
    this.hideLoading();
    this.clearStreamRetry();
  }
  
  /**
   * Handle stream error event
   */
  onStreamError() {
    this.setConnectionStatus('disconnected', 'Disconnected');
    console.error('Video stream error');
    this.scheduleStreamRetry();
  }
  
  /**
   * Check connection status
   */
  async checkConnection() {
    const timeoutMs = 5000;
    let timeoutId;
    let controller;
    let signal;

    if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') {
      signal = AbortSignal.timeout(timeoutMs);
    } else {
      controller = new AbortController();
      signal = controller.signal;
      timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    }

    try {
      const response = await fetch('/health', { signal });
      if (response.ok) {
        this.setConnectionStatus('connected', 'Connected');
      } else {
        this.setConnectionStatus('disconnected', 'Disconnected');
      }
    } catch {
      this.setConnectionStatus('disconnected', 'Disconnected');
    } finally {
      // Clear fallback timeout if it was set
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      // Note: AbortSignal.timeout() handles its own cleanup automatically
      // and cannot be manually cancelled once created
    }
  }
  
  /**
   * Set connection status
   */
  setConnectionStatus(status, text) {
    this.isConnected = status === 'connected';
    
    if (this.elements.statusIndicator) {
      this.elements.statusIndicator.className = 'status-indicator';
      this.elements.statusIndicator.classList.add(status);
    }
    
    if (this.elements.statusText) {
      this.elements.statusText.textContent = text;
    }
  }
  
  /**
   * Start stats update interval
   */
  startStatsUpdate() {
    if (this.updateInterval || this.pollingPausedForRetry) return;
    
    this.updateInterval = setInterval(() => {
      this.updateStats();
    }, this.updateFrequency);
  }
  
  /**
   * Stop stats update interval
   */
  stopStatsUpdate() {
    if (this.updateInterval) {
      clearInterval(this.updateInterval);
      this.updateInterval = null;
    }
  }
  
  /**
   * Calculate exponential backoff delay
   */
  calculateBackoffDelay(attempts = this.retryAttempts, baseDelay = this.baseDelay) {
    const exponentialDelay = baseDelay * Math.pow(2, attempts);
    // Add jitter (random delay up to 20% of the base delay)
    const jitter = Math.random() * baseDelay * 0.2;
    return Math.min(exponentialDelay + jitter, this.maxDelay);
  }

  /**
   * Schedule a stream refresh with exponential backoff
   */
  scheduleStreamRetry() {
    if (this.streamRetryTimeout) return;

    if (this.streamRetryAttempts >= this.maxRetries) {
      console.warn('Max stream retry attempts reached. Waiting for manual refresh.');
      return;
    }

    this.streamRetryAttempts += 1;
    const delay = this.calculateBackoffDelay(this.streamRetryAttempts, this.streamBaseDelay);
    console.log(`Retrying stream in ${(delay / 1000).toFixed(1)}s (attempt ${this.streamRetryAttempts}/${this.maxRetries})`);

    this.streamRetryTimeout = setTimeout(() => {
      this.streamRetryTimeout = null;
      this.refreshStream();
    }, delay);
  }

  /**
   * Clear scheduled stream retry
   */
  clearStreamRetry() {
    if (this.streamRetryTimeout) {
      clearTimeout(this.streamRetryTimeout);
      this.streamRetryTimeout = null;
    }
    this.streamRetryAttempts = 0;
  }
  
  /**
   * Fetch and update stats from /ready endpoint
   */
  async updateStats() {
    if (this.statsInFlight) return;
    
    try {
      this.statsInFlight = true;

    const timeoutMs = 5000;
    let timeoutId;
    let controller;
    let signal;

    if (this.retryTimeout) {
      clearTimeout(this.retryTimeout);
      this.retryTimeout = null;
    }

    if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') {
      signal = AbortSignal.timeout(timeoutMs);
    } else {
      controller = new AbortController();
      signal = controller.signal;
      timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    }

    try {
      const response = await fetch('/ready', {
        signal
      });

      if (!response.ok) {
        if (response.status === 503) {
          let notReadyPayload = null;
          try {
            notReadyPayload = await response.json();
          } catch (parseError) {
            console.warn('Failed to parse /ready 503 response:', parseError);
          }

          if (notReadyPayload?.status === 'not_ready') {
            const statusText = notReadyPayload?.reason || notReadyPayload?.message || 'Starting...';
            this.setConnectionStatus('connecting', statusText);
            this.statsInFlight = false;
            return;
          }
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      // Reset retry attempts on success
      this.retryAttempts = 0;
      if (this.retryTimeout) {
        clearTimeout(this.retryTimeout);
        this.retryTimeout = null;
      }
      if (this.pollingPausedForRetry) {
        this.pollingPausedForRetry = false;
        this.startStatsUpdate();
      }
      
      // Update connection status if not already connected
      if (!this.isConnected) {
        this.setConnectionStatus('connected', 'Connected');
      }
      
      // Update stats values
      if (this.elements.fpsValue) {
        this.elements.fpsValue.textContent = data.current_fps 
          ? data.current_fps.toFixed(1) 
          : '0.0';
      }
      
      if (this.elements.uptimeValue) {
        this.elements.uptimeValue.textContent = this.formatUptime(data.uptime_seconds);
      }
      
      if (this.elements.framesValue) {
        this.elements.framesValue.textContent = this.formatNumber(data.frames_captured);
      }

      if (this.elements.lastFrameAgeValue) {
        this.elements.lastFrameAgeValue.textContent = this.formatSeconds(
          data.last_frame_age_seconds
        );
      }

      if (this.elements.maxFrameAgeValue) {
        this.elements.maxFrameAgeValue.textContent = this.formatSeconds(
          data.max_frame_age_seconds
        );
      }
      
      if (this.elements.resolutionValue) {
        if (data.resolution && Array.isArray(data.resolution)) {
          this.elements.resolutionValue.textContent = 
            `${data.resolution[0]} × ${data.resolution[1]}`;
        }
      }
      
      if (this.elements.edgeDetectionValue) {
        const badge = this.elements.edgeDetectionValue;
        badge.textContent = data.edge_detection ? 'Enabled' : 'Disabled';
        badge.className = 'stat-badge';
        badge.classList.add(data.edge_detection ? 'enabled' : 'disabled');
      }
      
      // Update last updated timestamp
      if (this.elements.lastUpdated) {
        const now = new Date();
        this.elements.lastUpdated.textContent = 
          `Updated: ${now.toLocaleTimeString()}`;
      }
    } catch (error) {
      console.error('Failed to fetch stats:', error);
      this.setConnectionStatus('disconnected', 'Disconnected');
      
      // Show fallback values
      if (this.elements.fpsValue) {
        this.elements.fpsValue.textContent = '--';
      }

      if (this.elements.lastFrameAgeValue) {
        this.elements.lastFrameAgeValue.textContent = '--';
      }

      if (this.elements.maxFrameAgeValue) {
        this.elements.maxFrameAgeValue.textContent = '--';
      }
      
      // Implement exponential backoff retry
      if (this.retryAttempts < this.maxRetries) {
        this.retryAttempts++;
        const delay = this.calculateBackoffDelay();
        console.log(`Retrying in ${(delay / 1000).toFixed(1)}s (attempt ${this.retryAttempts}/${this.maxRetries})`);
        
        // Schedule retry
        this.stopStatsUpdate();
        this.pollingPausedForRetry = true;
        if (this.retryTimeout) {
          clearTimeout(this.retryTimeout);
        }
        this.retryTimeout = setTimeout(() => {
          this.updateStats();
        }, delay);
      } else {
        console.warn('Max retry attempts reached. Will retry on next scheduled update.');
        this.retryAttempts = 0; // Reset for next scheduled update
        if (this.pollingPausedForRetry) {
          this.pollingPausedForRetry = false;
          this.startStatsUpdate();
        }
      }
    } finally {
      // Clear fallback timeout if it was set
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      // Note: AbortSignal.timeout() handles its own cleanup automatically
      this.statsInFlight = false;
    }
  }
  
  /**
   * Format uptime in human-readable format
   */
  formatUptime(seconds) {
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
  formatNumber(num) {
    if (num === null || num === undefined) return '0';
    return num.toLocaleString();
  }

  /**
   * Format seconds with a consistent precision
   */
  formatSeconds(seconds) {
    if (seconds === null || seconds === undefined) return '--';
    if (Number.isNaN(seconds)) return '--';
    return `${Number(seconds).toFixed(2)}s`;
  }
  
  /**
   * Hide loading overlay
   */
  hideLoading() {
    const loadingOverlay = document.querySelector('.loading-overlay');
    if (loadingOverlay) {
      loadingOverlay.style.opacity = '0';
      setTimeout(() => {
        loadingOverlay.remove();
      }, 300);
    }
  }
}

// Initialize app when script loads
new CameraStreamApp();
