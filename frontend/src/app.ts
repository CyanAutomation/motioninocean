/**
 * motion-in-ocean - Camera Stream Application
 * Real-time stats, fullscreen, refresh, and connection monitoring
 */

import { renderConfig as renderConfigPanel } from "./config-renderer.js";
import { renderMetrics as renderMetricsPanel, type MetricsResponse } from "./metrics-renderer.js";
import { applyMockStreamMode as applyMockStreamModeUi } from "./mock-stream-ui.js";
import { assertSinglePollingMode as assertPollingState } from "./polling-mode.js";
import { collectSetupConfig as collectWizardConfig, type SetupConfig } from "./setup-config.js";
import {
  createDeviceDetectionSummary,
  inferSetupPreset,
  restoreSetupWizardState,
  setupWizardSteps,
  validateSetupStep,
  type DeviceDetectionPayload,
  type SetupWizardStep,
} from "./setup-wizard.js";
import {
  fetchReadmeContent as fetchReadmeHelp,
  renderMarkdownContent as renderReadmeMarkdown,
} from "./webcam-help.js";
import { toggleFullscreen as toggleFullscreenUi, type FullscreenDocument } from "./fullscreen.js";
import { generateSetupConfiguration } from "./setup-generation.js";
import { runConfigUpdate } from "./config-update.js";
import { loadSetupTemplates } from "./setup-load.js";
import { bindOptionalEventListeners, type OptionalEventBinding } from "./app-event-bindings.js";
import { showWebcamHelpModal } from "./webcam-help-modal.js";

const REQUEST_TIMEOUT_MS = 5000;
const CONFIG_POLL_INTERVAL_MS = 5000;
const THEME_STORAGE_KEY = "webcam.theme";
const DEFAULT_MIO_PATH = "/static/img/mio/mio_avatar.png";
const CHANGELOG_MAX_VISIBLE_ENTRIES = 3;

interface AppElements {
  [name: string]: HTMLElement | HTMLElement[] | null;
  availabilityDetail: HTMLElement | null;
  availabilityRiskValue: HTMLElement | null;
  chipConnected: HTMLElement | null;
  chipFps: HTMLElement | null;
  chipInactive: HTMLElement | null;
  chipStale: HTMLElement | null;
  configErrorAlert: HTMLElement | null;
  configErrorMessage: HTMLElement | null;
  configLoading: HTMLElement | null;
  configPanel: HTMLElement | null;
  configRefreshBtn: HTMLButtonElement | null;
  connectionChipValue: HTMLElement | null;
  fpsValue: HTMLElement | null;
  framesRiskDetail: HTMLElement | null;
  fullscreenBtn: HTMLButtonElement | null;
  lastFrameAgeValue: HTMLElement | null;
  lastFrameRiskValue: HTMLElement | null;
  lastUpdated: HTMLElement | null;
  maxFrameAgeValue: HTMLElement | null;
  maxFrameRiskValue: HTMLElement | null;
  mioHeroImage: HTMLImageElement | null;
  mockStreamAnimation: HTMLImageElement | null;
  mockStreamPlaceholder: HTMLElement | null;
  performanceRiskValue: HTMLElement | null;
  railChangelogBtn: HTMLButtonElement | null;
  railHelpBtn: HTMLButtonElement | null;
  refreshBtn: HTMLButtonElement | null;
  refreshStreamHeaderBtn: HTMLButtonElement | null;
  resolutionValue: HTMLElement | null;
  settingsPanel: HTMLElement | null;
  setupPanel: HTMLElement | null;
  statsPanel: HTMLElement | null;
  statusIndicator: HTMLElement | null;
  statusText: HTMLElement | null;
  streamRiskValue: HTMLElement | null;
  tabButtons: HTMLButtonElement[] | null;
  themeIconMoon: HTMLElement | null;
  themeIconSun: HTMLElement | null;
  themeToggleBtn: HTMLButtonElement | null;
  toggleStatsBtn: HTMLButtonElement | null;
  uptimeValue: HTMLElement | null;
  utilityModal: HTMLElement | null;
  utilityModalCloseBtn: HTMLButtonElement | null;
  utilityModalContent: HTMLElement | null;
  utilityModalTitle: HTMLElement | null;
  videoStream: HTMLImageElement | null;
  viewSubtitle: HTMLElement | null;
  viewTitle: HTMLElement | null;
}

interface AppState {
  updateInterval: boolean | null;
  baseUpdateFrequency: number;
  updateFrequency: number;
  maxUpdateFrequency: number;
  consecutiveFailures: number;
  connectionTimeout: ReturnType<typeof setTimeout> | null;
  isConnected: boolean;
  statsCollapsed: boolean;
  statsInFlight: boolean;
  configInFlight: boolean;
  currentTab: string;
  lastConfigUpdate: Date | null;
  configPollingInterval: ReturnType<typeof setInterval> | null;
  configInitialLoadPending: boolean;
  configLoadingDelayTimer: ReturnType<typeof setTimeout> | null;
  configLoadingVisible: boolean;
  setupInitialLoadPending: boolean;
  setupLoadingDelayTimer: ReturnType<typeof setTimeout> | null;
  setupLoadingVisible: boolean;
  setupFormState: Partial<SetupConfig> & Record<string, unknown>;
  setupDetectedDevices: DeviceDetectionPayload;
  streamConnections: { current: string; max: string };
  previouslyFocusedElement: HTMLElement | null;
  utilityModalOpen: boolean;
  changelogCache: ChangelogPayload | null;
  elements: AppElements;
}

interface ChangelogEntry {
  changes: string[];
  release_date: string | null;
  version: string;
}

interface ChangelogPayload {
  entries: ChangelogEntry[];
  full_changelog_url?: string;
  message?: string;
  source?: string;
  status: string;
}

type DeviceConfiguration = Record<string, unknown> & { intent?: string };

const state: AppState = {
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
  previouslyFocusedElement: null,
  utilityModalOpen: false,
  changelogCache: null,
  elements: {
    videoStream: null,
    mockStreamPlaceholder: null,
    mockStreamAnimation: null,
    statsPanel: null,
    configPanel: null,
    settingsPanel: null,
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
    mioHeroImage: null,
    railChangelogBtn: null,
    railHelpBtn: null,
    utilityModal: null,
    utilityModalCloseBtn: null,
    utilityModalTitle: null,
    utilityModalContent: null,
    configLoading: null,
    configErrorAlert: null,
    configErrorMessage: null,
    // Cached tab buttons (set in cacheElements)
    tabButtons: null,
  },
};

let metricsEventSource: EventSource | null = null;

/**
 * Initialize the application
 */
function init() {
  cacheElements();
  attachHandlers();
  initializeTheme();
  updateViewMeta(state.currentTab);
  updateMascotForTab(state.currentTab);
  startStatsUpdate();
  // Fetch initial stats immediately so the panel is populated on first paint.
  // Ongoing updates are driven by the SSE connection opened in startStatsUpdate().
  updateStats().catch((error) => console.error("Initial stats update failed:", error));
  // Config data is only fetched when the user first switches to the config tab;
  // skip the cold-start pre-fetch to avoid a wasted API call on the main tab.

  console.log("motion-in-ocean camera stream initialized");
}

function getElementById<T extends HTMLElement = HTMLElement>(id: string): T | null {
  return document.getElementById(id) as T | null;
}

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function toSetupFormState(value: unknown): Partial<SetupConfig> & Record<string, unknown> {
  const record = asRecord(value);
  const config: Partial<SetupConfig> = {};
  if (typeof record.resolution === "string") config.resolution = record.resolution;
  if (typeof record.fps === "number") config.fps = record.fps;
  if (typeof record.jpeg_quality === "number") config.jpeg_quality = record.jpeg_quality;
  if (typeof record.max_connections === "number") config.max_connections = record.max_connections;
  if (typeof record.target_fps === "number" || record.target_fps === null) {
    config.target_fps = record.target_fps;
  }
  if (typeof record.pi3_profile === "boolean") config.pi3_profile = record.pi3_profile;
  if (typeof record.cors_origins === "string") config.cors_origins = record.cors_origins;
  if (typeof record.mock_camera === "boolean") config.mock_camera = record.mock_camera;
  if (typeof record.auth_token === "string") config.auth_token = record.auth_token;
  return { ...record, ...config };
}

function toDeviceDetectionPayload(value: unknown): DeviceDetectionPayload {
  const record = asRecord(value);
  const deviceList = (key: string): string[] | undefined =>
    Array.isArray(record[key])
      ? record[key].filter((entry): entry is string => typeof entry === "string")
      : undefined;
  return {
    video_devices: deviceList("video_devices"),
    media_devices: deviceList("media_devices"),
    dma_heap_devices: deviceList("dma_heap_devices"),
    vchiq_device: record.vchiq_device,
  };
}

/**
 * Apply theme mode to webcam page.
 *
 * Persists selected mode in localStorage and updates toggle label.
 *
 * @param {string} theme - Theme name ("light" or "dark").
 * @returns {void}
 */
function applyTheme(theme: string) {
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
  state.elements.videoStream = getElementById<HTMLImageElement>("video-stream");
  state.elements.mockStreamPlaceholder = getElementById("mock-stream-placeholder");
  state.elements.mockStreamAnimation = getElementById<HTMLImageElement>("mock-stream-animation");
  state.elements.statsPanel = getElementById("stats-panel");
  state.elements.configPanel = getElementById("config-panel");
  state.elements.settingsPanel = getElementById("settings-panel");
  state.elements.setupPanel = getElementById("setup-panel");
  state.elements.toggleStatsBtn = getElementById<HTMLButtonElement>("toggle-stats-btn");
  state.elements.refreshBtn = getElementById<HTMLButtonElement>("refresh-btn");
  state.elements.fullscreenBtn = getElementById<HTMLButtonElement>("fullscreen-btn");
  state.elements.refreshStreamHeaderBtn = getElementById<HTMLButtonElement>(
    "refresh-stream-header-btn",
  );
  state.elements.statusIndicator = getElementById("status-indicator");
  state.elements.statusText = getElementById("status-text");
  state.elements.themeToggleBtn = getElementById<HTMLButtonElement>("theme-toggle-btn");
  state.elements.themeIconMoon = getElementById("theme-icon-moon");
  state.elements.themeIconSun = getElementById("theme-icon-sun");
  state.elements.configRefreshBtn = getElementById<HTMLButtonElement>("config-refresh-btn");

  state.elements.fpsValue = getElementById("fps-value");
  state.elements.uptimeValue = getElementById("uptime-value");
  state.elements.framesRiskDetail = getElementById("frames-risk-detail");
  state.elements.lastFrameAgeValue = getElementById("last-frame-age-value");
  state.elements.maxFrameAgeValue = getElementById("max-frame-age-value");
  state.elements.resolutionValue = getElementById("resolution-value");
  state.elements.lastUpdated = getElementById("last-updated");
  state.elements.viewTitle = getElementById("webcam-view-title");
  state.elements.viewSubtitle = getElementById("webcam-view-subtitle");
  state.elements.connectionChipValue = getElementById("connection-chip-value");
  state.elements.performanceRiskValue = getElementById("performance-risk-value");
  state.elements.streamRiskValue = getElementById("stream-risk-value");
  state.elements.lastFrameRiskValue = getElementById("last-frame-risk-value");
  state.elements.maxFrameRiskValue = getElementById("max-frame-risk-value");
  state.elements.availabilityRiskValue = getElementById("availability-risk-value");
  state.elements.availabilityDetail = getElementById("availability-detail");

  // Header status chips
  state.elements.chipConnected = getElementById("chip-connected");
  state.elements.chipStale = getElementById("chip-stale");
  state.elements.chipInactive = getElementById("chip-inactive");
  state.elements.chipFps = getElementById("chip-fps");
  state.elements.mioHeroImage = getElementById<HTMLImageElement>("mio-hero-image");
  state.elements.railChangelogBtn = getElementById<HTMLButtonElement>("rail-changelog-btn");
  state.elements.railHelpBtn = getElementById<HTMLButtonElement>("rail-help-btn");
  state.elements.utilityModal = getElementById("utility-modal");
  state.elements.utilityModalCloseBtn =
    getElementById<HTMLButtonElement>("utility-modal-close-btn");
  state.elements.utilityModalTitle = getElementById("utility-modal-title");
  state.elements.utilityModalContent = getElementById("utility-modal-content");

  // Config panel elements
  state.elements.configLoading = getElementById("config-loading");
  state.elements.configErrorAlert = getElementById("config-error-alert");
  state.elements.configErrorMessage = getElementById("config-error-message");

  // Cache tab buttons to avoid a repeated DOM query on every tab switch
  state.elements.tabButtons = Array.from(document.querySelectorAll<HTMLButtonElement>(".tab-btn"));

  if (state.elements.mockStreamAnimation) {
    state.elements.mockStreamAnimation.onerror = () => {
      state.elements.mockStreamAnimation?.classList.add("mock-stream-animation--failed");
    };

    state.elements.mockStreamAnimation.onload = () => {
      state.elements.mockStreamAnimation?.classList.remove("mock-stream-animation--failed");
    };
  }
}

/**
 * Attach event listeners
 */
function attachHandlers() {
  const themeToggle = () => {
    const currentTheme = document.documentElement.getAttribute("data-theme") || "light";
    applyTheme(currentTheme === "dark" ? "light" : "dark");
  };
  const clickBindings: OptionalEventBinding[] = [
    { target: state.elements.toggleStatsBtn, type: "click", listener: toggleStats },
    { target: state.elements.refreshBtn, type: "click", listener: refreshStream },
    { target: state.elements.refreshStreamHeaderBtn, type: "click", listener: refreshStream },
    { target: state.elements.fullscreenBtn, type: "click", listener: toggleFullscreen },
    { target: state.elements.themeToggleBtn, type: "click", listener: themeToggle },
    { target: state.elements.configRefreshBtn, type: "click", listener: refreshConfigPanel },
    { target: state.elements.railChangelogBtn, type: "click", listener: openChangelogModal },
    { target: state.elements.railHelpBtn, type: "click", listener: openHelpModal },
    { target: state.elements.utilityModalCloseBtn, type: "click", listener: closeUtilityModal },
  ];

  // Proxy buttons inside the video controls mirror the main action buttons.
  const vcRefreshBtn = getElementById<HTMLButtonElement>("vc-refresh-btn");
  const vcFullscreenBtn = getElementById<HTMLButtonElement>("vc-fullscreen-btn");
  clickBindings.push(
    { target: vcRefreshBtn, type: "click", listener: refreshStream },
    { target: vcFullscreenBtn, type: "click", listener: toggleFullscreen },
  );

  const eventBindings: OptionalEventBinding[] = [
    ...clickBindings,
    {
      target: state.elements.utilityModal,
      type: "click",
      listener: (event: Event) => {
        if (event.target === state.elements.utilityModal) {
          closeUtilityModal();
        }
      },
    },
  ];
  eventBindings.push(
    { target: state.elements.videoStream, type: "load", listener: onStreamLoad },
    { target: state.elements.videoStream, type: "error", listener: onStreamError },
  );
  bindOptionalEventListeners(eventBindings);

  // Tab navigation handlers
  document.querySelectorAll<HTMLButtonElement>(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tab = btn.getAttribute("data-tab");
      if (tab) switchTab(tab);
    });
  });

  bindOptionalEventListeners(
    ["fullscreenchange", "webkitfullscreenchange", "mozfullscreenchange", "MSFullscreenChange"].map(
      (type) => ({ target: document, type, listener: onFullscreenChange }),
    ),
  );

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && state.utilityModalOpen) {
      closeUtilityModal();
      return;
    }

    if (event.key === "Tab" && state.utilityModalOpen) {
      trapUtilityModalTabCycle(event);
    }
  });

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
 * Open the shared utility modal with dynamic title and content.
 *
 * @param {{title: string, htmlContent: string}} options - Modal display options.
 * @param {string} options.title - Dialog heading text.
 * @param {string} options.htmlContent - HTML content to render in the modal body.
 * @returns {void}
 */
function openUtilityModal({ title, htmlContent }: { title: string; htmlContent: string }) {
  if (
    !state.elements.utilityModal ||
    !state.elements.utilityModalTitle ||
    !state.elements.utilityModalContent
  ) {
    return;
  }

  state.previouslyFocusedElement =
    document.activeElement instanceof HTMLElement ? document.activeElement : null;

  state.elements.utilityModalTitle.textContent = title;
  state.elements.utilityModalContent.textContent = "";
  // Use DOMParser for safe HTML rendering
  const parser = new DOMParser();
  const doc = parser.parseFromString(htmlContent, "text/html");
  const fragment = document.createDocumentFragment();
  Array.from(doc.body.childNodes).forEach((node) => {
    fragment.appendChild(node.cloneNode(true));
  });

  if (fragment.childNodes.length > 0) {
    state.elements.utilityModalContent.appendChild(fragment);
  } else {
    state.elements.utilityModalContent.appendChild(document.createTextNode(htmlContent));
  }

  state.elements.utilityModal.classList.remove("hidden");
  state.elements.utilityModal.hidden = false;
  state.utilityModalOpen = true;

  if (state.elements.utilityModalCloseBtn) {
    state.elements.utilityModalCloseBtn.focus();
  }
}

/**
 * Load README help content from API.
 *
 * @returns {Promise<{status: string, content: string, message: string, documentation_url: string, source: string}>} Normalized help payload.
 * @throws {Error} If the API request fails.
 * @async
 */
function fetchReadmeContent() {
  return fetchReadmeHelp();
}

/**
 * Close the utility modal and restore previous focus target.
 *
 * @returns {void}
 */
function closeUtilityModal() {
  if (!state.elements.utilityModal) {
    return;
  }

  state.elements.utilityModal.classList.add("hidden");
  state.elements.utilityModal.hidden = true;
  state.utilityModalOpen = false;

  if (
    state.previouslyFocusedElement &&
    typeof state.previouslyFocusedElement.focus === "function"
  ) {
    state.previouslyFocusedElement.focus();
  }
  state.previouslyFocusedElement = null;
}

/**
 * Keep keyboard tab navigation within the open utility modal.
 *
 * @param {KeyboardEvent} event - Keydown event for Tab navigation.
 * @returns {void}
 */
function trapUtilityModalTabCycle(event: KeyboardEvent) {
  if (!state.elements.utilityModal) {
    return;
  }

  const focusableElements = state.elements.utilityModal.querySelectorAll<HTMLElement>(
    'a[href], area[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
  );

  if (focusableElements.length === 0) {
    return;
  }

  const firstElement = focusableElements[0];
  const lastElement = focusableElements[focusableElements.length - 1];
  const activeElement = document.activeElement;

  if (event.shiftKey && activeElement === firstElement) {
    event.preventDefault();
    lastElement.focus();
    return;
  }

  if (!event.shiftKey && activeElement === lastElement) {
    event.preventDefault();
    firstElement.focus();
  }
}

/**
 * Load changelog entries from API with in-memory caching.
 *
 * @returns {Promise<{status: string, entries: Array<{version: string, release_date: string|null, changes: string[]}>, message?: string, full_changelog_url?: string}>} Changelog payload.
 * @throws {Error} If the API request fails.
 * @async
 */
async function fetchChangelogData(): Promise<ChangelogPayload> {
  if (state.changelogCache) {
    return state.changelogCache;
  }

  const response = await fetch("/api/changelog", {
    headers: {
      Accept: "application/json",
    },
  });

  const payload = (await response.json()) as ChangelogPayload;
  if (!response.ok && payload.status !== "degraded") {
    throw new Error(payload.message || "Failed to load changelog");
  }

  state.changelogCache = payload;
  return payload;
}

/**
 * Render changelog entries as release cards for modal display.
 *
 * @param {{status: string, entries: Array<{version: string, release_date: string|null, changes: string[]}>, message?: string, full_changelog_url?: string}} payload - Changelog API payload.
 * @returns {string} Safe HTML string for modal content.
 */
function renderChangelogHtml(payload: ChangelogPayload): string {
  const entries = Array.isArray(payload.entries) ? payload.entries : [];
  const visibleEntries = entries.slice(0, CHANGELOG_MAX_VISIBLE_ENTRIES);
  const debugModeEnabled = isDebugModeEnabled();

  const cardsHtml = visibleEntries
    .map((entry) => {
      const releaseDate = entry.release_date || "Unknown date";
      const releaseTitle = `v${entry.version}`;
      const changes = Array.isArray(entry.changes) ? entry.changes : [];
      const itemsHtml =
        changes.length > 0
          ? changes.map((change) => `<li>${escapeHtml(change)}</li>`).join("")
          : "<li>No release notes available.</li>";

      return [
        '<article class="changelog-card">',
        `<h3>${escapeHtml(releaseTitle)}</h3>`,
        `<p class="utility-subtle">${escapeHtml(releaseDate)}</p>`,
        `<ul>${itemsHtml}</ul>`,
        "</article>",
      ].join("");
    })
    .join("");

  const statusNote =
    payload.status === "degraded" ? renderDegradedChangelogNote(payload, debugModeEnabled) : "";

  const fullChangelogUrl =
    typeof payload.full_changelog_url === "string" ? payload.full_changelog_url.trim() : "";

  const fullChangelogLink = fullChangelogUrl
    ? `<p><a href="${escapeHtml(fullChangelogUrl)}" target="_blank" rel="noopener noreferrer">View full changelog</a></p>`
    : "";

  return [
    '<section class="changelog-list">',
    statusNote,
    cardsHtml || "<p>No changelog entries available.</p>",
    fullChangelogLink,
    "</section>",
  ].join("");
}

/**
 * Determine whether debug mode is enabled for the current page.
 *
 * @returns {boolean} True when debug query parameter is truthy.
 */
function isDebugModeEnabled() {
  const debugParam = new URLSearchParams(window.location.search).get("debug");
  return ["1", "true", "yes", "on"].includes((debugParam || "").toLowerCase());
}

/**
 * Render a user-friendly degraded changelog note.
 *
 * Includes diagnostic details only when debug mode is enabled.
 *
 * @param {{message?: string, source?: string}} payload - Changelog API payload.
 * @param {boolean} debugModeEnabled - Whether debug diagnostics should be shown.
 * @returns {string} Safe degraded status note markup.
 */
function renderDegradedChangelogNote(payload: ChangelogPayload, debugModeEnabled: boolean): string {
  const userFriendlyMessage =
    "We couldn't load the latest changelog details right now. Try again shortly.";

  if (!debugModeEnabled) {
    return `<p class="utility-subtle">${escapeHtml(userFriendlyMessage)}</p>`;
  }

  const debugDetails = [payload.message, payload.source].filter(Boolean).join(" | ");
  const debugLine = debugDetails
    ? `<br><span class="utility-subtle">Debug: ${escapeHtml(debugDetails)}</span>`
    : "";
  return `<p class="utility-subtle">${escapeHtml(userFriendlyMessage)}${debugLine}</p>`;
}

/**
 * Render trusted README markdown into sanitized HTML for modal display.
 *
 * Supports a lightweight subset used by project README documents:
 * headings, paragraphs, fenced code blocks, unordered/ordered lists,
 * inline code, emphasis, and links.
 *
 * @param {string} markdown - Trusted markdown content returned by /api/help/readme.
 * @returns {string} Sanitized HTML output for modal rendering.
 */
function renderMarkdownContent(markdown: string): string {
  return renderReadmeMarkdown(markdown);
}

/**
 * Sanitize rendered utility HTML with an allowlist-based policy.
 *
 * Removes disallowed tags/attributes, strips event handler attributes,
 * rejects unsafe link protocols, and enforces rel protections for
 * external links.
 *
 * @param {string} html - Potentially unsafe HTML content.
 * @returns {string} Sanitized HTML safe for modal rendering.
 */
function sanitizeUtilityHtml(html: string): string {
  const allowedTags = new Set([
    "a",
    "article",
    "blockquote",
    "br",
    "code",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "li",
    "ol",
    "p",
    "pre",
    "strong",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
  ]);

  const parser = new DOMParser();
  const parsedDocument = parser.parseFromString(String(html || ""), "text/html");
  const outputDocument = document.implementation.createHTMLDocument("");

  const sanitizeNode = (node: Node): Node | null => {
    if (node.nodeType === Node.TEXT_NODE) {
      return outputDocument.createTextNode(node.textContent || "");
    }

    if (node.nodeType !== Node.ELEMENT_NODE) {
      return null;
    }

    const sourceElement = node as Element;
    const tagName = sourceElement.tagName.toLowerCase();
    const childNodes = Array.from(sourceElement.childNodes)
      .map((child) => sanitizeNode(child))
      .filter((child): child is Node => child !== null);

    if (!allowedTags.has(tagName)) {
      const fragment = outputDocument.createDocumentFragment();
      childNodes.forEach((child) => fragment.appendChild(child));
      return fragment;
    }

    const sanitizedElement = outputDocument.createElement(tagName);

    if (tagName === "article" && sourceElement.classList.contains("utility-modal__markdown")) {
      sanitizedElement.setAttribute("class", "utility-modal__markdown");
    }

    if (tagName === "a") {
      const safeHref = sanitizeAnchorHref(sourceElement.getAttribute("href") || "");
      if (safeHref) {
        sanitizedElement.setAttribute("href", safeHref);

        if (isExternalNavigationLink(safeHref)) {
          sanitizedElement.setAttribute("target", "_blank");
          sanitizedElement.setAttribute("rel", "noopener noreferrer");
        }
      }
    }

    childNodes.forEach((child) => sanitizedElement.appendChild(child));
    return sanitizedElement;
  };

  const wrapper = outputDocument.createElement("div");
  Array.from(parsedDocument.body.childNodes)
    .map((child) => sanitizeNode(child))
    .filter((child): child is Node => child !== null)
    .forEach((child) => wrapper.appendChild(child));

  return wrapper.innerHTML;
}

/**
 * Validate anchor href values for safe navigation.
 *
 * @param {string} href - Link href candidate.
 * @returns {string} Safe href value, or empty string when rejected.
 */
function sanitizeAnchorHref(href: string): string {
  const raw = String(href || "").trim();
  if (!raw) {
    return "";
  }

  // eslint-disable-next-line no-control-regex
  const normalized = raw.replace(/[\u0000-\u001F\u007F\s]+/g, "");
  if (!normalized) {
    return "";
  }

  if (/^[a-zA-Z][a-zA-Z\d+\-.]*:/.test(normalized)) {
    try {
      const parsed = new URL(normalized);
      return ["http:", "https:"].includes(parsed.protocol) ? raw : "";
    } catch {
      return "";
    }
  }

  return raw;
}

/**
 * Determine whether a link points to an external destination.
 *
 * @param {string} href - Sanitized anchor href value.
 * @returns {boolean} True for external absolute HTTP(S) URLs.
 */
function isExternalNavigationLink(href: string): boolean {
  if (!href) {
    return false;
  }

  try {
    const parsed = new URL(href, window.location.origin);
    const isHttp = ["http:", "https:"].includes(parsed.protocol);
    return isHttp && parsed.origin !== window.location.origin;
  } catch {
    return false;
  }
}

/**
 * Render inline markdown tokens into escaped HTML.
 *
 * @param {string} text - Single-line markdown text.
 * @returns {string} Escaped and transformed inline HTML.
 */
/**
 * Open the changelog utility modal.
 *
 * @returns {Promise<void>} Promise resolving when changelog is rendered.
 * @async
 */
async function openChangelogModal() {
  openUtilityModal({
    title: "Changelog",
    htmlContent: "<p>Loading changelog…</p>",
  });

  try {
    const payload = await fetchChangelogData();
    openUtilityModal({
      title: "Changelog",
      htmlContent: renderChangelogHtml(payload),
    });
  } catch (error) {
    openUtilityModal({
      title: "Changelog",
      htmlContent: `<p>Unable to load changelog: ${escapeHtml(error instanceof Error ? error.message : String(error))}</p>`,
    });
  }
}

/**
 * Open the help utility modal.
 *
 * @returns {Promise<void>} Promise resolving when help content is rendered.
 * @async
 */
async function openHelpModal() {
  await showWebcamHelpModal({
    fetchReadme: fetchReadmeContent,
    openModal: openUtilityModal,
    renderMarkdown: renderMarkdownContent,
    sanitizeHtml: sanitizeUtilityHtml,
    escapeHtml,
    warn: (message, error) => console.warn(message, error),
  });
}

/**
 * Ensure only one polling mode is active at a time.
 */
function assertSinglePollingMode() {
  return assertPollingState({
    sse: metricsEventSource !== null,
    config: state.configPollingInterval !== null,
    timestamp: false,
  });
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
      requestAnimationFrame(() => renderMetrics(data));
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") {
        console.warn("Stats request timed out, will retry.");
        increaseBackoff();
        return;
      }

      handleStatsUpdateError(error);
      return;
    }
  } finally {
    state.statsInFlight = false;
  }
}

/** Render the disconnected state after a failed metrics request. */
function handleStatsUpdateError(error: unknown) {
  console.error("Failed to fetch stats:", error);
  setConnectionStatus("disconnected", "Disconnected");
  increaseBackoff();

  const placeholderIds = [
    "fpsValue",
    "uptimeValue",
    "framesRiskDetail",
    "lastFrameAgeValue",
    "maxFrameAgeValue",
    "resolutionValue",
    "lastUpdated",
    "performanceRiskValue",
    "lastFrameRiskValue",
    "maxFrameRiskValue",
  ];
  placeholderIds.forEach((elementKey) => {
    const element = state.elements[elementKey];
    if (element instanceof HTMLElement) {
      element.textContent = "--";
    }
  });
  if (state.elements.streamRiskValue) state.elements.streamRiskValue.textContent = "Offline";
  if (state.elements.availabilityRiskValue) {
    state.elements.availabilityRiskValue.textContent = "Offline";
  }
  if (state.elements.availabilityDetail) {
    state.elements.availabilityDetail.textContent = "-- connections";
  }
  updateConnectionDisplays();
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
 * Refresh the video stream.
 *
 * Resets stream src to force reload.
 * Animates refresh button on click.
 *
 * @returns {void}
 */
function refreshStream() {
  if (!state.elements.videoStream) return;

  const streamUrl = state.elements.videoStream.src.split("?")[0];
  state.elements.videoStream.src = streamUrl;

  const refreshButton = state.elements.refreshBtn;
  if (refreshButton) {
    refreshButton.style.transform = "rotate(360deg)";
    setTimeout(() => {
      refreshButton.style.transform = "";
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
async function toggleFullscreen() {
  const container = state.elements.videoStream?.closest<HTMLElement>(".video-container") ?? null;
  await toggleFullscreenUi(container, document as FullscreenDocument);
}

/**
 * Handle fullscreen change events
 */
function onFullscreenChange() {
  const fullscreenDocument = document as FullscreenDocument;
  const isFullscreen = !!(
    fullscreenDocument.fullscreenElement ||
    fullscreenDocument.webkitFullscreenElement ||
    fullscreenDocument.mozFullScreenElement ||
    fullscreenDocument.msFullscreenElement
  );

  if (state.elements.fullscreenBtn) {
    const btnText = state.elements.fullscreenBtn.querySelector(".control-btn-text");
    if (btnText) {
      btnText.textContent = isFullscreen ? "Exit Fullscreen" : "Fullscreen";
    }
    const btnIcon = state.elements.fullscreenBtn.querySelector(".control-btn-icon");
    if (btnIcon) {
      btnIcon.textContent = "⛶";
    }
  }

  const vcFullscreenBtn = document.getElementById("vc-fullscreen-btn");
  if (vcFullscreenBtn) {
    vcFullscreenBtn.textContent = isFullscreen ? "Exit Fullscreen" : "Fullscreen";
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
function setConnectionStatus(status: string, text: string): void {
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
 * Open a Server-Sent Events connection to /api/metrics/stream.
 *
 * Replaces the setInterval polling loop. The server pushes a metrics event every
 * 3 seconds over a single persistent HTTP connection (~30× fewer requests/min).
 * EventSource reconnects automatically on transient failures. DOM updates are
 * scheduled via requestAnimationFrame to batch all writes into a single paint frame.
 *
 * @returns {void}
 */
function startMetricsStream() {
  if (metricsEventSource) return;
  if (state.statsCollapsed || document.hidden) return;

  metricsEventSource = new EventSource("/api/metrics/stream");

  metricsEventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      // Batch all DOM writes into a single paint frame
      requestAnimationFrame(() => renderMetrics(data));
    } catch (e) {
      console.error("Failed to parse metrics SSE data:", e);
    }
  };

  metricsEventSource.onerror = () => {
    setConnectionStatus("disconnected", "Reconnecting...");
    // EventSource.CLOSED means it will NOT reconnect; clear our reference so
    // the next startMetricsStream() call creates a fresh connection.
    if (metricsEventSource && metricsEventSource.readyState === EventSource.CLOSED) {
      metricsEventSource = null;
    }
  };
}

/**
 * Close the Server-Sent Events metrics stream connection.
 *
 * @returns {void}
 */
function stopMetricsStream() {
  if (metricsEventSource) {
    metricsEventSource.close();
    metricsEventSource = null;
  }
}

/**
 * Start stats update connection.
 *
 * Opens the SSE stream for ongoing metric pushes.
 * Skips if stream already open, stats collapsed, or page hidden.
 *
 * @returns {void}
 */
function startStatsUpdate() {
  if (state.updateInterval) return;
  if (state.statsCollapsed || document.hidden) return;

  // Sentinel so assertSinglePollingMode() stays consistent with legacy callers
  state.updateInterval = true;
  startMetricsStream();
}

/**
 * Stop stats update connection.
 *
 * Closes the SSE stream and clears the sentinel interval flag.
 *
 * @returns {void}
 */
function stopStatsUpdate() {
  stopMetricsStream();
  state.updateInterval = null;
}

/**
 * Set stats polling frequency and restart timer if active.
 *
 * Retained for backoff compatibility; has no effect on the SSE stream interval
 * which is controlled server-side.
 *
 * @param {number} nextFrequency - Polling frequency in milliseconds (unused by SSE).
 * @returns {void}
 */
function setUpdateFrequency(nextFrequency: number): void {
  if (state.updateFrequency === nextFrequency) return;
  state.updateFrequency = nextFrequency;
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
function renderMetrics(data: MetricsResponse): void {
  renderMetricsPanel(data, {
    state,
    setConnectionStatus,
    resetBackoff,
    increaseBackoff,
    formatUptime,
    formatNumber,
    formatSeconds,
    updateConnectionDisplays,
  });
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
function formatConnectionValue(value: number | string | null | undefined): string {
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
function formatUptime(seconds: number | undefined): string {
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
function formatNumber(num: number | undefined): string {
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
function formatSeconds(seconds: number | undefined): string {
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
  const loadingOverlay = document.querySelector<HTMLElement>(".loading-overlay");
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
function switchTab(tabName: string): void {
  const wasConfigTab = state.currentTab === "config";
  const wasSetupTab = state.currentTab === "setup";
  state.currentTab = tabName;

  updateTabButtons(tabName);

  updateViewMeta(tabName);
  updateMascotForTab(tabName);

  // Update visible panels
  const mainSection = document.querySelector<HTMLElement>(".video-section");
  const statsPanel = state.elements.statsPanel;
  const configPanel = state.elements.configPanel;
  const settingsPanel = state.elements.settingsPanel;
  const setupPanel = state.elements.setupPanel;

  setTabPanelVisibility(tabName, {
    mainSection,
    statsPanel,
    configPanel,
    settingsPanel,
    setupPanel,
  });
  activateTabServices(tabName, { wasConfigTab, wasSetupTab });

  assertSinglePollingMode();
}

/** Update active state on all tab buttons. */
function updateTabButtons(tabName: string): void {
  const tabButtons =
    state.elements.tabButtons ??
    Array.from(document.querySelectorAll<HTMLButtonElement>(".tab-btn"));
  tabButtons.forEach((btn) => {
    btn.classList.toggle("active", btn.getAttribute("data-tab") === tabName);
  });
}

/** Show the panel associated with a tab and hide the others. */
function setTabPanelVisibility(
  tabName: string,
  panels: {
    mainSection: HTMLElement | null;
    statsPanel: HTMLElement | null;
    configPanel: HTMLElement | null;
    settingsPanel: HTMLElement | null;
    setupPanel: HTMLElement | null;
  },
): void {
  const { mainSection, statsPanel, configPanel, settingsPanel, setupPanel } = panels;
  const panelMap: Record<string, Array<HTMLElement | null>> = {
    main: [mainSection, statsPanel],
    config: [configPanel],
    settings: [settingsPanel],
    setup: [setupPanel],
  };
  const visiblePanel = panelMap[tabName] || [];
  [mainSection, statsPanel, configPanel, settingsPanel, setupPanel].forEach((panel) => {
    if (panel) panel.classList.toggle("hidden", !visiblePanel.includes(panel));
  });
}

/** Start and stop services required by the selected tab. */
function activateTabServices(
  tabName: string,
  { wasConfigTab, wasSetupTab }: { wasConfigTab: boolean; wasSetupTab: boolean },
): void {
  if (tabName === "main") {
    stopConfigPolling();
    if (!state.statsCollapsed) startStatsUpdate();
    return;
  }
  stopStatsUpdate();
  if (tabName === "config" && !wasConfigTab) {
    state.configInitialLoadPending = true;
    updateConfig().catch((error) => console.error("Config update failed:", error));
    startConfigPolling();
  } else if (tabName === "setup" && !wasSetupTab) {
    state.setupInitialLoadPending = true;
    loadSetupTab().catch((error) => console.error("Setup tab load failed:", error));
  }
  if (tabName === "settings") stopConfigPolling();
  if (tabName === "setup") stopConfigPolling();
}

/**
 * Resolve mascot image assets provided on the page.
 *
 * @returns {{avatar: string, happy: string, curious: string, sleeping: string, winking: string, floating: string}}
 */
function getMioAssets(): Record<
  "avatar" | "curious" | "floating" | "happy" | "sleeping" | "winking",
  string
> {
  const { dataset } = document.body;
  return {
    avatar: dataset.mioAvatar || DEFAULT_MIO_PATH,
    happy: dataset.mioHappy || DEFAULT_MIO_PATH,
    curious: dataset.mioCurious || DEFAULT_MIO_PATH,
    sleeping: dataset.mioSleeping || DEFAULT_MIO_PATH,
    winking: dataset.mioWinking || DEFAULT_MIO_PATH,
    floating: dataset.mioFloating || DEFAULT_MIO_PATH,
  };
}

/**
 * Update mascot image(s) based on active tab.
 *
 * @param {string} tabName - Active view key.
 * @returns {void}
 */
function updateMascotForTab(tabName: string): void {
  const assets = getMioAssets();
  const mascotByTab: Record<string, { src: string; alt: string }> = {
    main: {
      src: assets.happy,
      alt: "Mio mascot for Stream view",
    },
    config: {
      src: assets.curious,
      alt: "Mio mascot for Configuration view",
    },
    setup: {
      src: assets.avatar,
      alt: "Mio mascot for Set-Up view",
    },
    settings: {
      src: assets.sleeping,
      alt: "Mio mascot for Runtime Settings view",
    },
  };

  const mascot = mascotByTab[tabName] || mascotByTab.main;
  const imageElement = state.elements.mioHeroImage;
  if (!imageElement) return;
  imageElement.src = mascot.src;
  imageElement.alt = mascot.alt;
}

/**
 * Update view title and subtitle to reflect active webcam view.
 *
 * @param {string} tabName - Active view key.
 * @returns {void}
 */
function updateViewMeta(tabName: string): void {
  const titleByTab: Record<string, string> = {
    main: "Stream",
    config: "Configuration",
    setup: "Set-Up",
    settings: "Runtime Settings",
  };
  const subtitleByTab: Record<string, string> = {
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
  await runConfigUpdate(state, {
    isActive: state.currentTab === "config" && !document.hidden,
    loadingElement: state.elements.configLoading,
    fetchConfig,
    renderConfig,
    clearConfigDisplay,
    showConfigError,
    logger: console,
    onSuccess: () => {
      if (state.elements.configErrorAlert) {
        state.elements.configErrorAlert.classList.add("hidden");
      }
    },
  });
}

/**
 * Show error alert in config panel with message.
 *
 * Displays error message in config error alert element.
 *
 * @param {string} message - Error message to display.
 * @returns {void}
 */
function showConfigError(message: string): void {
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
function renderConfig(data: unknown): void {
  renderConfigPanel(asRecord(data) as Parameters<typeof renderConfigPanel>[0], {
    state,
    setConfigValue,
    formatBoolean,
    formatUptime,
    applyMockStreamMode,
    setHealthIndicator,
    normalizeHealthState,
    healthText: HEALTH_TEXT,
    updateConnectionDisplays,
  });
}

/**
 * Toggle stream/placeholder visibility based on runtime mock camera state.
 *
 * @param {boolean} isMockModeActive - Whether mock camera mode should be shown.
 * @param {boolean} isFallbackActive - Whether active mock fallback is currently in use.
 * @returns {void}
 */
function applyMockStreamMode(isMockModeActive: boolean, isFallbackActive: boolean): void {
  applyMockStreamModeUi(isMockModeActive, isFallbackActive, {
    elements: state.elements,
    document,
    setConnectionStatus,
  });
}

const HEALTH_TEXT = {
  ok: "OK",
  warn: "Warning",
  fail: "Failing",
  unknown: "Unknown",
};

function normalizeHealthState(stateValue: unknown): "fail" | "ok" | "unknown" | "warn" {
  const normalized = String(stateValue || "").toLowerCase();

  if (["ok", "pass", "healthy", "ready"].includes(normalized)) return "ok";
  if (["warn", "warning", "degraded"].includes(normalized)) return "warn";
  if (["fail", "error", "failed", "down", "unhealthy"].includes(normalized)) return "fail";
  return "unknown";
}

function setHealthIndicator(elementId: string, indicator: unknown): void {
  const element = getElementById(elementId);
  if (!element) return;

  const indicatorRecord = asRecord(indicator);
  const stateKey = normalizeHealthState(indicatorRecord.state);
  const labelText =
    typeof indicatorRecord.label === "string" && indicatorRecord.label.trim().length > 0
      ? indicatorRecord.label
      : HEALTH_TEXT[stateKey];

  element.textContent = labelText;
  element.className = `config-value health-indicator health-${stateKey}`;
  element.setAttribute("data-health-state", stateKey);

  const detailText =
    typeof indicatorRecord.details === "string" ? indicatorRecord.details.trim() : "";
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
function setConfigValue(elementId: string, value: string | number): void {
  const element = getElementById(elementId);
  if (!element) return;

  element.textContent = String(value);

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
function formatBoolean(value: boolean | null | undefined): string {
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

const setupWizard: {
  storageKey: string;
  steps: readonly SetupWizardStep[];
  currentStep: SetupWizardStep;
  expertMode: boolean;
  initialized: boolean;
} = {
  storageKey: "motioninocean.setupWizard.v1",
  steps: [...setupWizardSteps],
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
function getWizardStateFromStorage(): unknown {
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
      piVersion: getElementById<HTMLInputElement>("env-pi-version")?.value || "",
      intent: getElementById<HTMLSelectElement>("env-intent")?.value || "",
      mockCamera: getElementById<HTMLSelectElement>("env-mock-camera")?.value || "false",
    },
    preset: getElementById<HTMLSelectElement>("preset-select")?.value || "custom",
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
  const restored = restoreSetupWizardState(getWizardStateFromStorage(), {
    steps: setupWizard.steps,
    currentStep: setupWizard.currentStep,
    expertMode: setupWizard.expertMode,
    setValue: (id, value) => {
      const input = getElementById<HTMLInputElement | HTMLSelectElement>(id);
      if (input && value !== undefined && value !== null) {
        input.value = String(value);
      }
    },
    setChecked: (id, checked) => {
      const input = getElementById<HTMLInputElement>(id);
      if (input) {
        input.checked = checked;
      }
    },
    applyFields: applyConfigToForm,
  });

  if (restored) {
    setupWizard.expertMode = restored.expertMode;
    setupWizard.currentStep = restored.currentStep;
  }
}

/**
 * Collect setup wizard configuration from form inputs.
 *
 * @returns {Object} Configuration object with resolution, fps, quality settings.
 */
function collectSetupConfig(): SetupConfig {
  return collectWizardConfig(document);
}

/**
 * Apply configuration values to setup form inputs.
 *
 * @param {Object} config - Configuration object with setup values.
 * @returns {void}
 */
function applyConfigToForm(config: Partial<SetupConfig>): void {
  if (!config || typeof config !== "object") return;

  const setValue = (id: string, value: string | number | boolean | null | undefined): void => {
    const el = getElementById<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>(id);
    if (el !== null && el !== undefined && value !== undefined && value !== null) {
      el.value = String(value);
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
function inferPresetFromEnvironment(): string {
  const piVersion = getElementById<HTMLInputElement>("env-pi-version")?.value;
  const intent = getElementById<HTMLSelectElement>("env-intent")?.value;
  return inferSetupPreset(piVersion || "", intent || "");
}

/**
 * Apply a preset configuration to the setup form.
 *
 * @param {string} preset - Preset name ("pi3_low_power", "pi5_high_quality", "custom").
 * @returns {void}
 */
function applyPresetToForm(preset: string): void {
  const envMockCamera = getElementById<HTMLSelectElement>("env-mock-camera")?.value || "false";

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

function getStepIndex(step: SetupWizardStep): number {
  return setupWizard.steps.indexOf(step);
}

/**
 * Navigate to a wizard step, updating UI and saving state.
 *
 * @param {string} step - Step name (e.g., "environment", "preset", "review").
 * @returns {void}
 */
function setWizardStep(step: SetupWizardStep): void {
  if (!setupWizard.steps.includes(step)) return;
  setupWizard.currentStep = step;

  document.querySelectorAll<HTMLElement>(".wizard-step-panel").forEach((panel) => {
    panel.classList.toggle("hidden", panel.getAttribute("data-step-panel") !== step);
  });

  document.querySelectorAll<HTMLElement>(".wizard-step").forEach((stepButton) => {
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
function validateStep(step: SetupWizardStep): boolean {
  const value = (id: string): string =>
    getElementById<HTMLInputElement | HTMLSelectElement>(id)?.value || "";
  return validateSetupStep(step, setupWizard.expertMode, {
    piVersion: value("env-pi-version"),
    intent: value("env-intent"),
    preset: value("preset-select"),
    resolution: value("setup-resolution"),
    fps: value("setup-fps"),
  });
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
  const prevBtn = getElementById<HTMLButtonElement>("setup-prev-btn");
  const nextBtn = getElementById<HTMLButtonElement>("setup-next-btn");

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

function escapeHtml(unsafe: unknown): string {
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
  const recommendation = getElementById("preset-recommendation");
  if (recommendation) {
    recommendation.textContent = `Recommended from environment answers: ${recommendedPreset}`;
  }

  const presetSelect = getElementById<HTMLSelectElement>("preset-select");
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

  const piVersion = getElementById<HTMLInputElement>("env-pi-version")?.value || "not selected";
  const intent = getElementById<HTMLSelectElement>("env-intent")?.value || "not selected";
  const preset = getElementById<HTMLSelectElement>("preset-select")?.value || "custom";
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
  await loadSetupTemplates({
    panelAvailable: Boolean(state.elements.setupPanel),
    fetchTemplates: async () => {
      const response = await fetch("/api/setup/templates");
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    },
    setLoading: (isLoading) => {
      const loading = document.getElementById("setup-loading");
      if (loading) loading.classList.toggle("hidden", !isLoading);
    },
    applyTemplates: (data) => {
      const templates = asRecord(data);
      state.setupFormState = toSetupFormState(templates.current_config);
      state.setupDetectedDevices = toDeviceDetectionPayload(templates.detected_devices);
      updateSetupUI(templates);
      applyStoredWizardState();
      updatePresetRecommendation();
    },
    isInitialized: () => setupWizard.initialized,
    initializeEventListeners: () => {
      attachSetupEventListeners();
      setupWizard.initialized = true;
    },
    setWizardStep: () => setWizardStep(setupWizard.currentStep),
    setStatus: (status) => {
      const statusDot = document.getElementById("setup-status-indicator");
      const statusText = document.getElementById("setup-status-text");
      if (statusDot) {
        statusDot.className =
          status === "ready" ? "setup-status-dot ready" : "setup-status-dot error";
      }
      if (statusText)
        statusText.textContent = status === "ready" ? "Setup ready" : "Setup load failed";
    },
    onError: (error) => {
      const message = error instanceof Error ? error.message : String(error);
      showSetupError(`Failed to load setup: ${message}`);
    },
    logger: console,
  });
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
function getDeviceDetectionSummary(
  devices: DeviceDetectionPayload = {},
  currentConfig: DeviceConfiguration = {},
) {
  const configuredIntent = typeof currentConfig.intent === "string" ? currentConfig.intent : "";
  const modeIntent = getElementById<HTMLSelectElement>("env-intent")?.value || configuredIntent;
  return createDeviceDetectionSummary(devices, currentConfig, modeIntent);
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
function renderDeviceStatus(
  devices: DeviceDetectionPayload = {},
  currentConfig: DeviceConfiguration = {},
): void {
  const deviceStatus = getElementById("device-status");
  if (!deviceStatus) return;

  const summary = getDeviceDetectionSummary(devices, currentConfig);

  const checklistItems = [
    {
      label: "Video devices (/dev/video*)",
      passed: summary.videoCount > 0,
      detail: summary.videoCount > 0 ? (devices.video_devices || []).join(", ") : "None",
    },
    {
      label: "Media devices (/dev/media*)",
      passed: summary.mediaCount > 0,
      detail: summary.mediaCount > 0 ? (devices.media_devices || []).join(", ") : "None",
    },
    {
      label: "DMA heap",
      passed: summary.dmaCount > 0,
      detail: summary.dmaCount > 0 ? (devices.dma_heap_devices || []).join(", ") : "None",
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
  const rescanBtn = getElementById<HTMLButtonElement>("rescan-devices-btn");
  if (rescanBtn) {
    rescanBtn.disabled = true;
    rescanBtn.textContent = "Scanning...";
  }

  try {
    const response = await fetch("/api/setup/templates");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const data = asRecord(await response.json());
    state.setupDetectedDevices = toDeviceDetectionPayload(data.detected_devices);
    state.setupFormState = toSetupFormState(data.current_config || state.setupFormState);
    renderDeviceStatus(state.setupDetectedDevices, state.setupFormState);
  } catch (error) {
    console.error("Failed to rescan devices:", error);
    showSetupError(
      `Failed to re-scan devices: ${error instanceof Error ? error.message : String(error)}`,
    );
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
function updateSetupUI(data: Record<string, unknown>): void {
  const currentConfig = toSetupFormState(data.current_config);
  state.setupDetectedDevices = toDeviceDetectionPayload(
    data.detected_devices || state.setupDetectedDevices,
  );
  state.setupFormState = currentConfig;
  renderDeviceStatus(state.setupDetectedDevices, currentConfig);

  applyConfigToForm(currentConfig);

  if (typeof currentConfig.mock_camera === "boolean") {
    const mockCameraInput = getElementById<HTMLSelectElement>("env-mock-camera");
    if (mockCameraInput) mockCameraInput.value = currentConfig.mock_camera ? "true" : "false";
  }
}

function attachSetupEventListeners() {
  const presetSelect = getElementById<HTMLSelectElement>("preset-select");
  if (presetSelect) {
    presetSelect.addEventListener("change", (event) => {
      onPresetChange(event);
      updateReviewSummary();
      saveWizardState();
    });
  }

  const generateBtn = getElementById<HTMLButtonElement>("generate-btn");
  if (generateBtn) {
    generateBtn.addEventListener("click", onGenerateClick);
  }

  const expertToggle = getElementById<HTMLInputElement>("expert-mode-toggle");
  if (expertToggle) {
    expertToggle.addEventListener("change", () => {
      setupWizard.expertMode = expertToggle.checked;
      const advancedPanel = getElementById<HTMLDetailsElement>("advanced-review-panel");
      if (advancedPanel) advancedPanel.open = setupWizard.expertMode;
      updateWizardNavigation();
      updateWizardCompletion();
      saveWizardState();
    });
  }

  const nextBtn = getElementById<HTMLButtonElement>("setup-next-btn");
  if (nextBtn) nextBtn.addEventListener("click", onSetupNext);

  const prevBtn = getElementById<HTMLButtonElement>("setup-prev-btn");
  if (prevBtn) prevBtn.addEventListener("click", onSetupPrevious);

  const rescanBtn = getElementById<HTMLButtonElement>("rescan-devices-btn");
  if (rescanBtn) rescanBtn.addEventListener("click", rescanSetupDevices);

  document.querySelectorAll<HTMLButtonElement>(".wizard-step").forEach((btn) => {
    btn.addEventListener("click", () => {
      const requestedStep = btn.getAttribute("data-step");
      if (!setupWizard.steps.some((step) => step === requestedStep)) return;
      const step = requestedStep as SetupWizardStep;
      const requestedIndex = getStepIndex(step);
      const currentIndex = getStepIndex(setupWizard.currentStep);
      if (requestedIndex <= currentIndex || validateStep(setupWizard.currentStep)) {
        setWizardStep(step);
      }
    });
  });

  document.querySelectorAll<HTMLButtonElement>(".output-copy-btn").forEach((button) => {
    button.addEventListener("click", () => {
      const targetId = button.getAttribute("data-target");
      if (targetId) copyToClipboard(targetId, button);
    });
  });

  ["env-pi-version", "env-intent", "env-mock-camera"].forEach((id) => {
    const field = getElementById<HTMLInputElement | HTMLSelectElement>(id);
    if (!field) return;
    field.addEventListener("change", () => {
      if (id === "env-mock-camera") {
        const mockCameraField = getElementById<HTMLSelectElement>("setup-mock-camera");
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

  document.querySelectorAll<HTMLElement>("[data-field]").forEach((field) => {
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

function onPresetChange(event: Event): void {
  const target = event.currentTarget;
  if (!(target instanceof HTMLSelectElement)) return;
  const preset = target.value;
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
  const resolution = getElementById<HTMLInputElement>("setup-resolution")?.value || "";
  const fps = getElementById<HTMLInputElement>("setup-fps")?.value || "";

  if (resolution && !/^\d+x\d+$/i.test(resolution)) {
    console.warn("Invalid resolution format. Use WIDTHxHEIGHT (e.g., 640x480)");
  }

  const fpsNumber = Number.parseInt(fps, 10);
  if (fps && (Number.isNaN(Number(fps)) || fpsNumber < 0 || fpsNumber > 120)) {
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
    const result = await generateSetupConfiguration(config);
    if (result.kind === "validation-error") {
      showSetupError(`Validation errors: ${result.errors.join(", ")}`);
      return;
    }

    const dockerComposeOutput = getElementById<HTMLTextAreaElement>("docker-compose-output");
    if (dockerComposeOutput) dockerComposeOutput.value = result.dockerComposeYaml;

    const envOutput = getElementById<HTMLTextAreaElement>("env-output");
    if (envOutput) envOutput.value = result.envContent;

    showSetupSuccess("Configuration generated successfully!");
    saveWizardState();
  } catch (error) {
    console.error("Generation failed:", error);
    showSetupError(`Generation failed: ${error instanceof Error ? error.message : String(error)}`);
  }
}

/**
 * Copy textarea content to clipboard
 */
function copyToClipboard(targetId: string, buttonElement: HTMLButtonElement): void {
  const textarea = getElementById<HTMLTextAreaElement>(targetId);
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
function showSetupError(message: string): void {
  const errorAlert = getElementById("setup-error-alert");
  const errorMessage = getElementById("setup-error-message");

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
function showSetupSuccess(message: string): void {
  const successAlert = getElementById("setup-success-alert");
  const successMessage = getElementById("setup-success-message");

  if (successAlert && successMessage) {
    successMessage.textContent = message;
    successAlert.classList.remove("hidden");

    setTimeout(() => {
      successAlert.classList.add("hidden");
    }, 3000);
  }
}

declare global {
  interface Window {
    switchTab?: (tabName: string) => void;
  }
}

// settings.js remains a separate module and uses this tab boundary.
window.switchTab = switchTab;
document.addEventListener("DOMContentLoaded", init);
