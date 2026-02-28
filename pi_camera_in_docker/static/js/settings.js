/**
 * Settings Management UI Handler
 * Manages the Settings tab: loads schema, renders forms, handles saves, etc.
 * @global switchTab - Central tab switcher from app.js
 */
/* global switchTab */

/**
 * Build a render-ready summary model from `/api/settings/changes` response data.
 *
 * @param {Object} changesPayload - API payload containing `overridden` entries.
 * @param {Object|null} schemaPayload - Loaded settings schema, used for restartability lookup.
 * @returns {{items: Array<Object>, restartRequired: boolean}} Render model for summary block.
 */
function buildSettingsChangesSummaryModel(changesPayload, schemaPayload) {
  const overridden = Array.isArray(changesPayload?.overridden) ? changesPayload.overridden : [];
  const schemaProperties = schemaPayload || {};

  const items = overridden
    .filter((entry) => typeof entry?.category === "string" && typeof entry?.key === "string")
    .map((entry) => {
      const categorySchema = schemaProperties[entry.category];
      const keySchema = categorySchema?.properties?.[entry.key] || {};
      const restartable = keySchema.restartable === true;
      return {
        category: entry.category,
        key: entry.key,
        value: entry.value,
        envValue: entry.env_value,
        restartable,
      };
    });

  return {
    items,
    restartRequired: items.some((item) => item.restartable),
  };
}

const SettingsUI = (() => {
  // State
  let schema = null;
  let currentSettings = null;
  let formDirty = false;
  const dirtyFields = new Set();

  // DOM Elements
  const settingsTab = () => document.getElementById("settings-tab-btn");
  const settingsLoading = () => document.getElementById("settings-loading");
  const saveBtn = () => document.getElementById("settings-save-btn");
  const resetBtn = () => document.getElementById("settings-reset-btn");
  const errorAlert = () => document.getElementById("settings-error-alert");
  const successAlert = () => document.getElementById("settings-success-alert");
  const undoAlert = () => document.getElementById("settings-undo-alert");
  const undoMessage = () => document.getElementById("settings-undo-message");
  const undoBtn = () => document.getElementById("settings-undo-btn");
  const confirmModal = () => document.getElementById("settings-confirm-modal");
  const confirmList = () => document.getElementById("settings-confirm-change-list");
  const confirmCancelBtn = () => document.getElementById("settings-confirm-cancel-btn");
  const confirmSaveBtn = () => document.getElementById("settings-confirm-save-btn");
  const changesSummary = () => document.getElementById("settings-changes-summary");
  const changesList = () => document.getElementById("settings-changes-list");
  const restartWarning = () => document.getElementById("settings-restart-warning");

  let undoPatch = null;
  let undoTimeoutId = null;

  /**
   * Initialize Settings UI.
   *
   * Attaches event listeners to tab, buttons, and form toggles.
   * Called on module load (DOMContentLoaded or immediately).
   *
   * @returns {void}
   */
  const init = () => {
    // Register tab click handler
    if (settingsTab()) {
      settingsTab().addEventListener("click", onTabClick);
    }

    // Register action handlers
    if (saveBtn()) {
      saveBtn().addEventListener("click", onSave);
    }
    if (resetBtn()) {
      resetBtn().addEventListener("click", onReset);
    }
    if (undoBtn()) {
      undoBtn().addEventListener("click", onUndo);
    }
    if (confirmCancelBtn()) {
      confirmCancelBtn().addEventListener("click", () => closeConfirmModal(false));
    }
    if (confirmSaveBtn()) {
      confirmSaveBtn().addEventListener("click", () => closeConfirmModal(true));
    }
    if (confirmModal()) {
      confirmModal().addEventListener("click", (event) => {
        if (event.target === confirmModal()) {
          closeConfirmModal(false);
        }
      });
    }
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && confirmModal() && !confirmModal().classList.contains("hidden")) {
        closeConfirmModal(false);
      }
    });

    // Register section toggle handlers
    document.querySelectorAll(".settings-section-toggle").forEach((toggle) => {
      toggle.addEventListener("click", onSectionToggle);
    });

    // Register section header click handlers (toggle collapse)
    document.querySelectorAll(".settings-section-header").forEach((header) => {
      header.addEventListener("click", onSectionHeaderClick);
    });

    // Single delegated listener for all setting inputs.
    // Avoids attaching N listeners on every renderForm() call and accumulating
    // duplicates when the user switches tabs or re-opens the settings panel.
    const settingsPanel = document.getElementById("settings-panel");
    if (settingsPanel) {
      settingsPanel.addEventListener("input", (e) => {
        if (e.target.classList.contains("setting-input")) {
          onFieldChange(e);
        }
      });
    }
  };

  /**
   * Handle settings tab click.
   *
   * Switches to settings panel via central switchTab() handler, then loads
   * schema and current settings if not already loaded, then renders form.
   *
   * @async
   * @param {Event} e - Click event.
   * @returns {Promise<void>}
   */
  const onTabClick = async (e) => {
    e.preventDefault();

    // Switch to settings tab using central handler
    switchTab("settings");

    // Load data if not already loaded
    if (!schema || !currentSettings) {
      await loadSettings();
    }
  };

  /**
   * Load settings and schema from /api/settings and /api/settings/schema endpoints.
   *
   * Fetches in parallel, renders form, clears dirty state, displays success/error alert.
   *
   * @async
   * @returns {Promise<void>}
   * @throws {Error} If either endpoint fails or response is not OK.
   */
  const loadSettings = async () => {
    try {
      settingsLoading().classList.remove("hidden");

      // Fetch schema and current settings in parallel
      const [schemaResp, settingsResp] = await Promise.all([
        fetch("/api/v1/settings/schema"),
        fetch("/api/v1/settings"),
      ]);

      if (!schemaResp.ok || !settingsResp.ok) {
        throw new Error("Failed to load settings");
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
      await refreshChangesSummary();

      showSuccess("Settings loaded successfully");
    } catch (error) {
      console.error("Error loading settings:", error);
      showError("Failed to load settings: " + error.message);
    } finally {
      settingsLoading().classList.add("hidden");
    }
  };

  /**
   * Render all settings form sections.
   *
   * Renders Camera, Logging, Discovery, and Feature Flags sections.
   * Attaches change event listeners to all form inputs.
   *
   * @returns {void}
   */
  const renderForm = () => {
    if (!schema) return;

    // Camera Settings
    renderCameraSettings();

    // Logging Settings
    renderLoggingSettings();

    // Discovery Settings
    renderDiscoverySettings();

    // Note: change/input listeners are registered once via event delegation in init().
  };

  /**
   * Render Camera settings section.
   *
   * Populates resolution, FPS, JPEG quality, max connections, and max frame age inputs.
   *
   * @returns {void}
   */
  const renderCameraSettings = () => {
    const cameraSettings = currentSettings.camera || {};

    // Resolution
    const resolutionSelect = document.getElementById("setting-resolution");
    if (resolutionSelect) {
      resolutionSelect.value = cameraSettings.resolution || "";
    }

    // FPS
    const fpsSlider = document.getElementById("setting-fps");
    if (fpsSlider) {
      fpsSlider.value = cameraSettings.fps || 30;
      updateSliderDisplay(fpsSlider);
    }

    // JPEG Quality
    const qualitySlider = document.getElementById("setting-jpeg-quality");
    if (qualitySlider) {
      qualitySlider.value = cameraSettings.jpeg_quality || 85;
      updateSliderDisplay(qualitySlider);
    }

    // Max Connections
    const maxConnInput = document.getElementById("setting-max-connections");
    if (maxConnInput) {
      maxConnInput.value = cameraSettings.max_stream_connections || 2;
    }

    // Max Frame Age
    const frameAgeInput = document.getElementById("setting-max-frame-age");
    if (frameAgeInput) {
      frameAgeInput.value = cameraSettings.max_frame_age_seconds || 10;
    }
  };

  /**
   * Render Logging settings section.
   *
   * Populates log level, log format, and log identifiers inputs.
   *
   * @returns {void}
   */
  const renderLoggingSettings = () => {
    const loggingSettings = currentSettings.logging || {};

    // Log Level
    const logLevelSelect = document.getElementById("setting-log-level");
    if (logLevelSelect) {
      logLevelSelect.value = loggingSettings.log_level || "INFO";
    }

    // Log Format
    const logFormatSelect = document.getElementById("setting-log-format");
    if (logFormatSelect) {
      logFormatSelect.value = loggingSettings.log_format || "text";
    }

    // Include Identifiers
    const identifiersCheckbox = document.getElementById("setting-log-identifiers");
    if (identifiersCheckbox) {
      identifiersCheckbox.checked = loggingSettings.log_include_identifiers || false;
    }
  };

  /**
   * Render Discovery settings section.
   *
   * Populates discovery enabled, management URL, discovery token, and interval inputs.
   *
   * @returns {void}
   */
  const renderDiscoverySettings = () => {
    const discoverySettings = currentSettings.discovery || {};

    // Discovery Enabled
    const enabledCheckbox = document.getElementById("setting-discovery-enabled");
    if (enabledCheckbox) {
      enabledCheckbox.checked = discoverySettings.discovery_enabled || false;
    }

    // Management URL
    const urlInput = document.getElementById("setting-discovery-url");
    if (urlInput) {
      urlInput.value = discoverySettings.discovery_management_url || "http://127.0.0.1:8001";
    }

    // Discovery Token
    const tokenInput = document.getElementById("setting-discovery-token");
    if (tokenInput) {
      tokenInput.value = discoverySettings.discovery_token || "";
    }

    // Discovery Interval
    const intervalInput = document.getElementById("setting-discovery-interval");
    if (intervalInput) {
      intervalInput.value = discoverySettings.discovery_interval_seconds || 30;
    }
  };

  /**
   * Update slider value display element.
   *
   * Updates text element showing current slider value.
   *
   * @param {HTMLInputElement} slider - Slider input element.
   * @returns {void}
   */
  const updateSliderDisplay = (slider) => {
    const container = slider.parentElement;
    const display = container?.querySelector(".setting-value-display .setting-current-value");
    if (display) {
      display.textContent = slider.value;
    }
  };

  let _fieldChangeDebounce = null;

  /**
   * Handle field change event.
   *
   * Updates slider display immediately for live feedback. Debounces dirty tracking
   * and save button updates to avoid redundant synchronous DOM writes on rapid
   * keystrokes or slider drags.
   *
   * @param {Event} e - Input event from delegated form listener.
   * @returns {void}
   */
  const onFieldChange = (e) => {
    const input = e.target;

    // Immediate visual feedback for sliders
    if (input.classList.contains("setting-slider")) {
      updateSliderDisplay(input);
    }

    // Debounce dirty-state tracking so rapid events collapse into one update
    clearTimeout(_fieldChangeDebounce);
    _fieldChangeDebounce = setTimeout(() => {
      const category = input.dataset.category;
      const property = input.dataset.property;
      if (!category || !property) return;

      const fieldKey = `${category}.${property}`;
      dirtyFields.add(fieldKey);
      formDirty = true;
      updateSaveButton();
    }, 150);
  };

  /**
   * Update save button disabled state based on form dirty status.
   *
   * Disables save button if no changes, enables if form is dirty.
   *
   * @returns {void}
   */
  const updateSaveButton = () => {
    if (saveBtn()) {
      saveBtn().disabled = !formDirty;
    }
  };

  /**
   * Handle section toggle button click.
   *
   * Uses explicit pixel-height transitions instead of max-height for smooth,
   * correctly-timed collapse/expand animation on any content size.
   *
   * @param {Event} e - Click event from toggle button.
   * @returns {void}
   */
  const onSectionToggle = (e) => {
    e.stopPropagation();
    const toggle = e.currentTarget;
    const section = toggle.dataset.section;
    const content = document.querySelector(`.settings-section-content[data-section="${section}"]`);
    if (!content) return;

    const isExpanded = !content.classList.contains("collapsed");

    if (isExpanded) {
      // Collapsing: lock to explicit pixel height, then animate to 0
      content.style.height = content.scrollHeight + "px";
      // Force reflow so the subsequent height change triggers a CSS transition
      void content.offsetHeight;
      content.style.height = "0";
      content.classList.add("collapsed");
    } else {
      // Expanding: begin from 0, animate to measured target, then unlock to auto
      content.classList.remove("collapsed");
      const targetHeight = content.scrollHeight;
      content.style.height = "0";
      void content.offsetHeight;
      content.style.height = targetHeight + "px";
      content.addEventListener(
        "transitionend",
        () => {
          content.style.height = "auto";
        },
        { once: true },
      );
    }

    toggle.classList.toggle("collapsed");
  };

  /**
   * Handle section header click.
   *
   * Delegates to toggle button within header for collapse/expand.
   *
   * @param {Event} e - Click event from section header.
   * @returns {void}
   */
  const onSectionHeaderClick = (e) => {
    const header = e.currentTarget;
    const toggle = header.querySelector(".settings-section-toggle");
    if (toggle) {
      toggle.click();
    }
  };

  /**
   * Save changed settings via PATCH request.
   *
   * Collects dirty fields, builds patch payload, sends to /api/settings endpoint.
   * Handles 200 (success), 422 (requires restart), 400 (validation error) responses.
   * Updates form state and displays appropriate alert on completion.
   *
   * @async
   * @returns {Promise<void>}
   * @throws {Error} If request fails or response is unexpected status.
   */
  const onSave = async () => {
    if (!formDirty || dirtyFields.size === 0) {
      showWarning("No changes to save");
      return;
    }

    const pendingChanges = buildPendingChanges();
    if (pendingChanges.length === 0) {
      showWarning("No valid settings changes found");
      return;
    }

    const confirmed = await showSaveConfirmation(pendingChanges);
    if (!confirmed) {
      return;
    }

    const patch = buildPatchFromChanges(pendingChanges, "newValue");
    const snapshotPatch = buildPatchFromChanges(pendingChanges, "oldValue");

    try {
      saveBtn().disabled = true;

      // Send PATCH request
      const response = await fetch("/api/v1/settings", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      });

      if (response.status === 200) {
        const result = await response.json();
        currentSettings = result.settings;
        formDirty = false;
        dirtyFields.clear();
        setUndoState(snapshotPatch, pendingChanges);
        updateSaveButton();
        await refreshChangesSummary();
        showSuccess("Settings saved successfully!");
      } else if (response.status === 422) {
        // Requires restart
        const result = await response.json();
        currentSettings = result.settings;
        formDirty = false;
        dirtyFields.clear();
        setUndoState(snapshotPatch, pendingChanges);
        updateSaveButton();
        await refreshChangesSummary();
        showWarning(
          "Settings saved! Some changes require server restart:\n" +
            result.modified_on_restart.join("\n"),
        );
      } else if (response.status === 400) {
        const result = await response.json();
        const errors = result.validation_errors || {};
        const errorList = Object.entries(errors)
          .map(([key, msg]) => `${key}: ${msg}`)
          .join("\n");
        showError("Validation error:\n" + errorList);
      } else {
        throw new Error(`HTTP ${response.status}`);
      }
    } catch (error) {
      console.error("Error saving settings:", error);
      showError("Failed to save settings: " + error.message);
      saveBtn().disabled = false;
    }
  };

  /**
   * Reset all settings to default values.
   *
   * Requires user confirmation. Posts to /api/settings/reset endpoint.
   * Reloads settings and clears dirty state on success.
   *
   * @async
   * @returns {Promise<void>}
   * @throws {Error} If reset request fails.
   */
  const onReset = async () => {
    if (!confirm("Reset all settings to defaults? This cannot be undone.")) {
      return;
    }

    try {
      const response = await fetch("/api/v1/settings/reset", { method: "POST" });

      if (response.ok) {
        formDirty = false;
        dirtyFields.clear();
        updateSaveButton();
        await loadSettings();
        await refreshChangesSummary();
        showSuccess("Settings reset to defaults!");
      } else {
        throw new Error(`HTTP ${response.status}`);
      }
    } catch (error) {
      console.error("Error resetting settings:", error);
      showError("Failed to reset settings: " + error.message);
    }
  };

  /**
   * Display error alert message.
   *
   * Shows error alert with message, auto-hides after 8 seconds.
   *
   * @param {string} message - Error message to display.
   * @returns {void}
   */
  const showError = (message) => {
    const alert = errorAlert();
    const msgElement = document.getElementById("settings-error-message");
    if (alert && msgElement) {
      msgElement.textContent = message;
      alert.classList.remove("hidden");
      setTimeout(() => alert.classList.add("hidden"), 8000);
    }
  };

  /**
   * Display success alert message.
   *
   * Shows success alert with message, auto-hides after 6 seconds.
   *
   * @param {string} message - Success message to display.
   * @returns {void}
   */
  const showSuccess = (message) => {
    const alert = successAlert();
    const msgElement = document.getElementById("settings-success-message");
    if (alert && msgElement) {
      msgElement.textContent = message;
      alert.classList.remove("hidden");
      setTimeout(() => alert.classList.add("hidden"), 6000);
    }
  };

  /**
   * Display warning alert message.
   *
   * Shows info/warning message via showSuccess with ℹ️ prefix.
   *
   * @param {string} message - Warning message to display.
   * @returns {void}
   */
  const showWarning = (message) => {
    showSuccess("ℹ️ " + message);
  };

  /**
   * Format a setting value for human-readable display.
   *
   * @param {unknown} value - Raw setting value.
   * @returns {string} Formatted value string.
   */
  const formatSettingValue = (value) => {
    if (value === null || value === undefined || value === "") {
      return "(empty)";
    }
    if (typeof value === "boolean") {
      return value ? "true" : "false";
    }
    return String(value);
  };

  /**
   * Read normalized value from a settings input field.
   *
   * @param {HTMLInputElement|HTMLSelectElement|HTMLTextAreaElement} input - Input element.
   * @returns {unknown} Parsed value suitable for PATCH payload.
   */
  const getInputValue = (input) => {
    if (input.type === "checkbox") {
      return input.checked;
    }
    if (input.type === "number" || input.type === "range") {
      return parseFloat(input.value);
    }
    return input.value;
  };

  /**
   * Build pending settings changes from dirty field tracking.
   *
   * @returns {Array<{category: string, property: string, oldValue: unknown, newValue: unknown}>} Changes.
   */
  const buildPendingChanges = () => {
    const changes = [];
    for (const fieldKey of dirtyFields) {
      const [category, property] = fieldKey.split(".");
      const input = document.querySelector(
        `.setting-input[data-category="${category}"][data-property="${property}"]`,
      );
      if (!input) {
        continue;
      }
      const oldValue = currentSettings?.[category]?.[property];
      const newValue = getInputValue(input);
      changes.push({ category, property, oldValue, newValue });
    }
    return changes;
  };

  /**
   * Build a PATCH payload from change entries.
   *
   * @param {Array<{category: string, property: string, oldValue: unknown, newValue: unknown}>} changes - Change entries.
   * @param {"oldValue"|"newValue"} valueKey - Which value to map into payload.
   * @returns {Object} Patch payload object.
   */
  const buildPatchFromChanges = (changes, valueKey) => {
    return changes.reduce((patch, change) => {
      if (!patch[change.category]) {
        patch[change.category] = {};
      }
      patch[change.category][change.property] = change[valueKey];
      return patch;
    }, {});
  };

  let confirmModalResolver = null;

  /**
   * Render and open save confirmation modal.
   *
   * @param {Array<{category: string, property: string, oldValue: unknown, newValue: unknown}>} changes - Pending changes.
   * @returns {Promise<boolean>} True when user confirms save.
   */
  const showSaveConfirmation = (changes) => {
    if (!confirmModal() || !confirmList()) {
      return Promise.resolve(window.confirm("Save settings changes?"));
    }

    confirmList().innerHTML = "";
    changes.forEach((change) => {
      const li = document.createElement("li");
      li.className = "settings-confirm-change-item";
      li.innerHTML = `
        <span class="settings-confirm-change-path">${change.category}.${change.property}</span>
        <span class="settings-confirm-change-values">${formatSettingValue(change.oldValue)} → ${formatSettingValue(change.newValue)}</span>
      `;
      confirmList().appendChild(li);
    });

    confirmModal().classList.remove("hidden");

    return new Promise((resolve) => {
      confirmModalResolver = resolve;
      confirmSaveBtn()?.focus();
    });
  };

  /**
   * Close confirmation modal and resolve pending decision.
   *
   * @param {boolean} confirmed - Whether save was confirmed.
   * @returns {void}
   */
  const closeConfirmModal = (confirmed) => {
    if (confirmModal()) {
      confirmModal().classList.add("hidden");
    }
    if (confirmModalResolver) {
      confirmModalResolver(confirmed);
      confirmModalResolver = null;
    }
  };

  /**
   * Set undo state for the most recent successful save.
   *
   * @param {Object} snapshotPatch - Previous values patch to restore on undo.
   * @param {Array<{category: string, property: string}>} changes - Saved changes.
   * @returns {void}
   */
  const setUndoState = (snapshotPatch, changes) => {
    clearUndoState();
    undoPatch = snapshotPatch;

    if (undoMessage() && undoAlert()) {
      undoMessage().textContent = `Saved ${changes.length} change${changes.length === 1 ? "" : "s"}.`;
      undoAlert().classList.remove("hidden");
    }
    if (undoBtn()) {
      undoBtn().disabled = false;
    }

    undoTimeoutId = setTimeout(() => {
      clearUndoState();
    }, 45000);
  };

  /**
   * Clear undo state and hide undo status banner.
   *
   * @returns {void}
   */
  const clearUndoState = () => {
    undoPatch = null;
    if (undoTimeoutId) {
      clearTimeout(undoTimeoutId);
      undoTimeoutId = null;
    }
    if (undoAlert()) {
      undoAlert().classList.add("hidden");
    }
    if (undoBtn()) {
      undoBtn().disabled = false;
    }
  };

  /**
   * Undo the most recent saved settings patch.
   *
   * @async
   * @returns {Promise<void>}
   */
  const onUndo = async () => {
    if (!undoPatch) {
      showWarning("Nothing to undo");
      return;
    }

    try {
      if (undoBtn()) {
        undoBtn().disabled = true;
      }

      const response = await fetch("/api/v1/settings", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(undoPatch),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();
      currentSettings = result.settings;
      formDirty = false;
      dirtyFields.clear();
      renderForm();
      updateSaveButton();
      await refreshChangesSummary();
      clearUndoState();
      showSuccess("Last save undone successfully");
    } catch (error) {
      console.error("Error undoing save:", error);
      showError("Failed to undo save: " + error.message);
      if (undoBtn()) {
        undoBtn().disabled = false;
      }
    }
  };

  /**
   * Render settings changes summary from server-side overrides.
   *
   * @param {{items: Array<Object>, restartRequired: boolean}} model - Changes summary model.
   * @returns {void}
   */
  const renderChangesSummary = (model) => {
    if (!changesSummary() || !changesList() || !restartWarning()) {
      return;
    }

    changesList().innerHTML = "";
    if (!Array.isArray(model.items) || model.items.length === 0) {
      changesSummary().classList.add("hidden");
      restartWarning().classList.add("hidden");
      return;
    }

    model.items.forEach((item) => {
      const row = document.createElement("div");
      row.className = "settings-change-item";
      row.innerHTML = `
        <div class="settings-change-path">${item.category}.${item.key}</div>
        <div class="settings-change-values">
          <span class="settings-change-value">Current: ${String(item.value)}</span>
          <span class="settings-change-value">Default: ${String(item.envValue)}</span>
          ${item.restartable ? '<span class="settings-change-badge">Restart required</span>' : ""}
        </div>
      `;
      changesList().appendChild(row);
    });

    changesSummary().classList.remove("hidden");
    restartWarning().classList.toggle("hidden", !model.restartRequired);
  };

  /**
   * Refresh changes summary by querying /api/settings/changes.
   *
   * @async
   * @returns {Promise<void>}
   */
  const refreshChangesSummary = async () => {
    try {
      const response = await fetch("/api/v1/settings/changes");
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const changesData = await response.json();
      const model = buildSettingsChangesSummaryModel(changesData, schema);
      renderChangesSummary(model);
    } catch (error) {
      console.error("Error loading settings change summary:", error);
    }
  };

  return {
    init,
    loadSettings,
  };
})();

// Initialize when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", SettingsUI.init);
} else {
  SettingsUI.init();
}
