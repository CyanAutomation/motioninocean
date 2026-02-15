/**
 * Settings Management UI Handler
 * Manages the Settings tab: loads schema, renders forms, handles saves, etc.
 */

const SettingsUI = (() => {
  // State
  let schema = null;
  let currentSettings = null;
  let formDirty = false;
  const dirtyFields = new Set();

  // DOM Elements
  const settingsTab = () => document.getElementById('settings-tab-btn');
  const settingsPanel = () => document.getElementById('settings-panel');
  const settingsLoading = () => document.getElementById('settings-loading');
  const saveBtn = () => document.getElementById('settings-save-btn');
  const resetBtn = () => document.getElementById('settings-reset-btn');
  const errorAlert = () => document.getElementById('settings-error-alert');
  const successAlert = () => document.getElementById('settings-success-alert');

  /**
   * Initialize Settings UI
   */
  const init = () => {
    // Register tab click handler
    if (settingsTab()) {
      settingsTab().addEventListener('click', onTabClick);
    }

    // Register action handlers
    if (saveBtn()) {
      saveBtn().addEventListener('click', onSave);
    }
    if (resetBtn()) {
      resetBtn().addEventListener('click', onReset);
    }

    // Register section toggle handlers
    document.querySelectorAll('.settings-section-toggle').forEach((toggle) => {
      toggle.addEventListener('click', onSectionToggle);
    });

    // Register section header click handlers (toggle collapse)
    document.querySelectorAll('.settings-section-header').forEach((header) => {
      header.addEventListener('click', onSectionHeaderClick);
    });
  };

  /**
   * Load settings and schema when tab is clicked
   */
  const onTabClick = async (e) => {
    e.preventDefault();
    
    // Switch to settings tab
    document.querySelectorAll('[role="tabpanel"]').forEach((panel) => {
      panel.classList.add('hidden');
    });
    settingsPanel().classList.remove('hidden');

    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach((btn) => {
      btn.classList.remove('active');
    });
    settingsTab().classList.add('active');

    // Load data if not already loaded
    if (!schema || !currentSettings) {
      await loadSettings();
    }
  };

  /**
   * Load settings and schema from API
   */
  const loadSettings = async () => {
    try {
      settingsLoading().classList.remove('hidden');
      
      // Fetch schema and current settings in parallel
      const [schemaResp, settingsResp] = await Promise.all([
        fetch('/api/settings/schema'),
        fetch('/api/settings'),
      ]);

      if (!schemaResp.ok || !settingsResp.ok) {
        throw new Error('Failed to load settings');
      }

      const schemaData = await schemaResp.json();
      const settingsData = await settingsResp.json();

      schema = schemaData.schema;
      currentSettings = settingsData.settings;

      // Render form
      renderForm();
      formDirty = false;
      dirtyFields.clear();
      updateSaveButton();

      showSuccess('Settings loaded successfully');
    } catch (error) {
      console.error('Error loading settings:', error);
      showError('Failed to load settings: ' + error.message);
    } finally {
      settingsLoading().classList.add('hidden');
    }
  };

  /**
   * Render all form sections
   */
  const renderForm = () => {
    if (!schema) return;

    // Camera Settings
    renderCameraSettings();

    // Logging Settings
    renderLoggingSettings();

    // Discovery Settings
    renderDiscoverySettings();

    // Feature Flags
    renderFeatureFlags();

    // Attach change event handlers to all inputs
    document.querySelectorAll('.setting-input').forEach((input) => {
      input.addEventListener('change', onFieldChange);
      input.addEventListener('input', onFieldChange);
    });
  };

  /**
   * Render Camera section
   */
  const renderCameraSettings = () => {
    const cameraSettings = currentSettings.camera || {};
    

    // Resolution
    const resolutionSelect = document.getElementById('setting-resolution');
    if (resolutionSelect) {
      resolutionSelect.value = cameraSettings.resolution || '';
    }

    // FPS
    const fpsSlider = document.getElementById('setting-fps');
    if (fpsSlider) {
      fpsSlider.value = cameraSettings.fps || 30;
      updateSliderDisplay(fpsSlider);
    }

    // JPEG Quality
    const qualitySlider = document.getElementById('setting-jpeg-quality');
    if (qualitySlider) {
      qualitySlider.value = cameraSettings.jpeg_quality || 85;
      updateSliderDisplay(qualitySlider);
    }

    // Max Connections
    const maxConnInput = document.getElementById('setting-max-connections');
    if (maxConnInput) {
      maxConnInput.value = cameraSettings.max_stream_connections || 2;
    }

    // Max Frame Age
    const frameAgeInput = document.getElementById('setting-max-frame-age');
    if (frameAgeInput) {
      frameAgeInput.value = cameraSettings.max_frame_age_seconds || 10;
    }
  };

  /**
   * Render Logging section
   */
  const renderLoggingSettings = () => {
    const loggingSettings = currentSettings.logging || {};

    // Log Level
    const logLevelSelect = document.getElementById('setting-log-level');
    if (logLevelSelect) {
      logLevelSelect.value = loggingSettings.log_level || 'INFO';
    }

    // Log Format
    const logFormatSelect = document.getElementById('setting-log-format');
    if (logFormatSelect) {
      logFormatSelect.value = loggingSettings.log_format || 'text';
    }

    // Include Identifiers
    const identifiersCheckbox = document.getElementById('setting-log-identifiers');
    if (identifiersCheckbox) {
      identifiersCheckbox.checked = loggingSettings.log_include_identifiers || false;
    }
  };

  /**
   * Render Discovery section
   */
  const renderDiscoverySettings = () => {
    const discoverySettings = currentSettings.discovery || {};

    // Discovery Enabled
    const enabledCheckbox = document.getElementById('setting-discovery-enabled');
    if (enabledCheckbox) {
      enabledCheckbox.checked = discoverySettings.discovery_enabled || false;
    }

    // Management URL
    const urlInput = document.getElementById('setting-discovery-url');
    if (urlInput) {
      urlInput.value = discoverySettings.discovery_management_url || 'http://127.0.0.1:8001';
    }

    // Discovery Token
    const tokenInput = document.getElementById('setting-discovery-token');
    if (tokenInput) {
      tokenInput.value = discoverySettings.discovery_token || '';
    }

    // Discovery Interval
    const intervalInput = document.getElementById('setting-discovery-interval');
    if (intervalInput) {
      intervalInput.value = discoverySettings.discovery_interval_seconds || 30;
    }
  };

  /**
   * Render Feature Flags
   */
  const renderFeatureFlags = () => {
    const container = document.getElementById('feature-flags-container');
    if (!container || !schema.feature_flags) return;

    const flagSettings = currentSettings.feature_flags || {};
    const flagSchema = schema.feature_flags.properties || {};

    container.innerHTML = '';

    // Group flags by category
    const categories = {};
    for (const [flagName, flagDef] of Object.entries(flagSchema)) {
      const category = flagDef.category || 'Other';
      if (!categories[category]) categories[category] = [];
      categories[category].push({ name: flagName, def: flagDef });
    }

    // Render each category
    for (const [category, flags] of Object.entries(categories)) {
      const categoryDiv = document.createElement('div');
      categoryDiv.style.gridColumn = 'span 1';

      flags.forEach(({ name, def }) => {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'feature-flag-item';

        const toggleDiv = document.createElement('div');
        toggleDiv.className = 'feature-flag-toggle';

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'setting-input setting-checkbox';
        checkbox.id = `setting-flag-${name}`;
        checkbox.dataset.category = 'feature_flags';
        checkbox.dataset.property = name;
        checkbox.checked = flagSettings[name] || def.default || false;
        checkbox.addEventListener('change', onFieldChange);

        const label = document.createElement('label');
        label.className = 'feature-flag-label';
        label.htmlFor = checkbox.id;
        label.textContent = def.title || name;

        toggleDiv.appendChild(checkbox);
        toggleDiv.appendChild(label);

        const categoryBadge = document.createElement('div');
        categoryBadge.className = 'feature-flag-category';
        categoryBadge.textContent = category;

        const description = document.createElement('div');
        description.className = 'feature-flag-description';
        description.textContent = def.description || '';

        itemDiv.appendChild(toggleDiv);
        itemDiv.appendChild(categoryBadge);
        itemDiv.appendChild(description);

        if (def.warning) {
          const warning = document.createElement('div');
          warning.className = 'setting-hint';
          warning.textContent = '⚠️ ' + def.warning;
          itemDiv.appendChild(warning);
        }

        categoryDiv.appendChild(itemDiv);
      });

      container.appendChild(categoryDiv);
    }
  };

  /**
   * Update slider display value
   */
  const updateSliderDisplay = (slider) => {
    const container = slider.parentElement;
    const display = container?.querySelector('.setting-value-display .setting-current-value');
    if (display) {
      display.textContent = slider.value;
    }
  };

  /**
   * Handle field change
   */
  const onFieldChange = (e) => {
    const input = e.target;
    const category = input.dataset.category;
    const property = input.dataset.property;
    const fieldKey = `${category}.${property}`;

    dirtyFields.add(fieldKey);
    formDirty = true;
    updateSaveButton();

    // Update slider display if applicable
    if (input.classList.contains('setting-slider')) {
      updateSliderDisplay(input);
    }
  };

  /**
   * Update save button state
   */
  const updateSaveButton = () => {
    if (saveBtn()) {
      saveBtn().disabled = !formDirty;
    }
  };

  /**
   * Handle section toggle
   */
  const onSectionToggle = (e) => {
    e.stopPropagation();
    const toggle = e.currentTarget;
    const section = toggle.dataset.section;
    const content = document.querySelector(
      `.settings-section-content[data-section="${section}"]`
    );

    if (content) {
      content.classList.toggle('collapsed');
      toggle.classList.toggle('collapsed');
    }
  };

  /**
   * Handle section header click
   */
  const onSectionHeaderClick = (e) => {
    const header = e.currentTarget;
    const toggle = header.querySelector('.settings-section-toggle');
    if (toggle) {
      toggle.click();
    }
  };

  /**
   * Save settings
   */
  const onSave = async () => {
    if (!formDirty || dirtyFields.size === 0) {
      showWarning('No changes to save');
      return;
    }

    try {
      saveBtn().disabled = true;

      // Build patch payload
      const patch = {};
      for (const fieldKey of dirtyFields) {
        const [category, property] = fieldKey.split('.');
        if (!patch[category]) patch[category] = {};

        // Get value from form
        const input = document.querySelector(
          `.setting-input[data-category="${category}"][data-property="${property}"]`
        );
        if (!input) continue;

        let value;
        if (input.type === 'checkbox') {
          value = input.checked;
        } else if (input.type === 'number' || input.type === 'range') {
          value = parseFloat(input.value);
        } else {
          value = input.value;
        }

        patch[category][property] = value;
      }

      // Send PATCH request
      const response = await fetch('/api/settings', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(patch),
      });

      if (response.status === 200) {
        const result = await response.json();
        currentSettings = result.settings;
        formDirty = false;
        dirtyFields.clear();
        updateSaveButton();
        showSuccess('Settings saved successfully!');
      } else if (response.status === 422) {
        // Requires restart
        const result = await response.json();
        currentSettings = result.settings;
        formDirty = false;
        dirtyFields.clear();
        updateSaveButton();
        showWarning(
          'Settings saved! Some changes require server restart:\n' +
            result.modified_on_restart.join('\n')
        );
      } else if (response.status === 400) {
        const result = await response.json();
        const errors = result.validation_errors || {};
        const errorList = Object.entries(errors)
          .map(([key, msg]) => `${key}: ${msg}`)
          .join('\n');
        showError('Validation error:\n' + errorList);
      } else {
        throw new Error(`HTTP ${response.status}`);
      }
    } catch (error) {
      console.error('Error saving settings:', error);
      showError('Failed to save settings: ' + error.message);
      saveBtn().disabled = false;
    }
  };

  /**
   * Reset settings
   */
  const onReset = async () => {
    if (!confirm('Reset all settings to defaults? This cannot be undone.')) {
      return;
    }

    try {
      const response = await fetch('/api/settings/reset', { method: 'POST' });

      if (response.ok) {
        formDirty = false;
        dirtyFields.clear();
        updateSaveButton();
        await loadSettings();
        showSuccess('Settings reset to defaults!');
      } else {
        throw new Error(`HTTP ${response.status}`);
      }
    } catch (error) {
      console.error('Error resetting settings:', error);
      showError('Failed to reset settings: ' + error.message);
    }
  };

  /**
   * Show error alert
   */
  const showError = (message) => {
    const alert = errorAlert();
    const msgElement = document.getElementById('settings-error-message');
    if (alert && msgElement) {
      msgElement.textContent = message;
      alert.classList.remove('hidden');
      setTimeout(() => alert.classList.add('hidden'), 8000);
    }
  };

  /**
   * Show success alert
   */
  const showSuccess = (message) => {
    const alert = successAlert();
    const msgElement = document.getElementById('settings-success-message');
    if (alert && msgElement) {
      msgElement.textContent = message;
      alert.classList.remove('hidden');
      setTimeout(() => alert.classList.add('hidden'), 6000);
    }
  };

  /**
   * Show warning alert (reuse success for now)
   */
  const showWarning = (message) => {
    showSuccess('ℹ️ ' + message);
  };

  return {
    init,
    loadSettings,
  };
})();

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', SettingsUI.init);
} else {
  SettingsUI.init();
}
