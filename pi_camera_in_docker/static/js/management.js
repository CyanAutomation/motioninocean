/**
 * Motion In Ocean Management Dashboard
 *
 * BUI for managing remote camera nodes, including registration, discovery, status monitoring,
 * diagnostics, and remote action execution. Implements webcam CRUD operations, bearer token
 * authentication, and real-time status polling.
 */

const tableBody = document.getElementById('webcams-table-body');
const webcamForm = document.getElementById('webcam-form');
const feedback = document.getElementById('form-feedback');
const formTitle = document.getElementById('form-title');
const cancelEditBtn = document.getElementById('cancel-edit-btn');
const refreshBtn = document.getElementById('refresh-webcams-btn');
const toggleWebcamFormPanelBtn = document.getElementById('toggle-webcam-form-panel-btn');
const managementLayout = document.getElementById('management-layout');
const webcamFormPanelContainer = document.getElementById('webcam-form-panel-container');
const webcamFormContentWrapper = document.getElementById('webcam-form-content-wrapper');
const webcamFormContent = document.getElementById('webcam-form-content');
const editingWebcamIdInput = document.getElementById('editing-webcam-id');
const diagnosticWebcamId = document.getElementById('diagnostic-webcam-id');
const diagnosticContext = document.getElementById('diagnostic-context');
const diagnosticSummaryBadge = document.getElementById('diagnostic-summary-badge');
const diagnosticOverallStatePill = document.getElementById('diagnostic-overall-state-pill');
const diagnosticSummaryInterpretation = document.getElementById(
  'diagnostic-summary-interpretation'
);
const diagnosticSummaryCta = document.getElementById('diagnostic-summary-cta');
const diagnosticChecksGrid = document.getElementById('diagnostic-checks-grid');
const diagnosticRecommendations = document.getElementById('diagnostic-recommendations');
const copyDiagnosticReportBtn = document.getElementById('copy-diagnostic-report-btn');
const diagnosticPanel = document.getElementById('diagnostic-panel');
const advancedDiagnosticsToggle = document.getElementById('advanced-diagnostics-toggle');
const diagnosticPanelContent = document.getElementById('diagnostic-panel-content');
const diagnosticsAdvancedCheckbox = advancedDiagnosticsToggle;
const diagnosticsCollapsibleContainer = diagnosticPanelContent;
const managementMain = document.getElementById('management-main');
const overviewView = document.getElementById('overview-view');
const devicesView = document.getElementById('devices-view');
const discoveredView = document.getElementById('discovered-view');
const settingsView = document.getElementById('settings-view');
const overviewTotalWebcams = document.getElementById('overview-total-webcams');
const overviewHealthyWebcams = document.getElementById('overview-healthy-webcams');
const overviewUnavailableWebcams = document.getElementById('overview-unavailable-webcams');
const overviewStreamingWebcams = document.getElementById('overview-streaming-webcams');
const overviewActivityList = document.getElementById('overview-activity-list');
const overviewActionList = document.getElementById('overview-action-list');
const refreshDashboardBtn = document.getElementById('refresh-dashboard-btn');
const scanDiscoveredBtn = document.getElementById('scan-discovered-btn');
const discoveredList = document.getElementById('discovered-list');
const discoveredNotes = document.getElementById('discovered-notes');
const discoveredFeedback = document.getElementById('discovered-feedback');
const discoveredApproveBtn = document.getElementById('discovered-approve-btn');
const discoveredRejectBtn = document.getElementById('discovered-reject-btn');
const discoveredLaterBtn = document.getElementById('discovered-later-btn');
const viewOverviewBtn = document.getElementById('view-overview-btn');
const viewDevicesBtn = document.getElementById('view-devices-btn');
const viewDiscoveredBtn = document.getElementById('view-discovered-btn');
const viewSettingsBtn = document.getElementById('view-settings-btn');
const railOverviewBtn = document.getElementById('rail-overview-btn');
const railDevicesBtn = document.getElementById('rail-devices-btn');
const railDiscoveredBtn = document.getElementById('rail-discovered-btn');
const railSettingsBtn = document.getElementById('rail-settings-btn');
const railExportBtn = document.getElementById('rail-export-btn');
const railHelpBtn = document.getElementById('rail-help-btn');
const mobileOverviewBtn = document.getElementById('mobile-overview-btn');
const mobileDevicesBtn = document.getElementById('mobile-devices-btn');
const mobileDiscoveredBtn = document.getElementById('mobile-discovered-btn');
const mobileSettingsBtn = document.getElementById('mobile-settings-btn');
const mobileExportBtn = document.getElementById('mobile-export-btn');
const mobileHelpBtn = document.getElementById('mobile-help-btn');
const themeToggleBtn = document.getElementById('theme-toggle-btn');
const refreshSettingsBtn = document.getElementById('refresh-settings-btn');
const settingsSaveBtn = document.getElementById('settings-save-btn');
const settingsResetBtn = document.getElementById('settings-reset-btn');
const settingsFeedback = document.getElementById('settings-feedback');
const settingsManagementApiToken = document.getElementById('settings-management-api-token');
const settingsDiscoveryEnabled = document.getElementById('settings-discovery-enabled');
const settingsDiscoveryUrl = document.getElementById('settings-discovery-url');
const settingsDiscoveryToken = document.getElementById('settings-discovery-token');
const settingsDiscoveryInterval = document.getElementById('settings-discovery-interval');
const settingsRuntimeSummary = document.getElementById('settings-runtime-summary');
const settingsValidationSummary = document.getElementById('settings-validation-summary');
const settingsOverridesList = document.getElementById('settings-overrides-list');
const settingsTabButtons = document.querySelectorAll('[data-settings-tab]');
const settingsAuthPanel = document.getElementById('settings-auth-panel');
const settingsDiscoveryPanel = document.getElementById('settings-discovery-panel');
const settingsRuntimePanel = document.getElementById('settings-runtime-panel');
const utilityPanel = document.getElementById('utility-panel');
const utilityPanelTitle = document.getElementById('utility-panel-title');
const utilityPanelContent = document.getElementById('utility-panel-content');
const utilityPanelCloseBtn = document.getElementById('utility-panel-close-btn');
const managementApiTokenInput = document.getElementById('management-api-token');

let webcams = [];
let webcamStatusMap = new Map();
let webcamStatusAggregationMap = new Map();
let statusRefreshInFlight = false;
let statusRefreshPending = false;
let statusRefreshPendingManual = false;
let statusRefreshToken = 0;
let statusRefreshIntervalId;
let latestDiagnosticResult = null;
let overviewSnapshot = null;
let currentSettingsPayload = null;
let selectedDiscoveredNodeId = '';
let activityFeed = [];
let previousStatusByNode = new Map();
let discoveredSnoozedIds = new Set();
let managementApiBearerToken = '';
const API_AUTH_HINT =
  'Management API request unauthorized. Provide a valid Management API Bearer Token, then click Refresh to retry.';

const DOCKER_BASE_URL_PATTERN = String.raw`docker://[^\s/:]+:\d+/[^\s/]+`;
const DOCKER_BASE_URL_HINT = 'Use format: docker://proxy-hostname:port/container-id';
const NODE_FORM_COLLAPSED_STORAGE_KEY = 'management.webcamFormCollapsed';
const VIEW_HASH_PREFIX = '#';
const VIEWS = ['overview', 'devices', 'discovered', 'settings'];
const THEME_STORAGE_KEY = 'management.theme';
const API_TOKEN_STORAGE_KEY = 'management.apiToken';
const SNOOZE_STORAGE_KEY = 'management.discoveredSnoozedIds';

function setDiagnosticPanelExpanded(isExpanded) {
  if (
    !(diagnosticsAdvancedCheckbox instanceof HTMLInputElement) ||
    !(diagnosticsCollapsibleContainer instanceof HTMLElement)
  ) {
    return;
  }

  diagnosticsAdvancedCheckbox.checked = isExpanded;
  diagnosticsCollapsibleContainer.hidden = !isExpanded;
  diagnosticsCollapsibleContainer.classList.toggle('hidden', !isExpanded);

  if (diagnosticPanel instanceof HTMLElement) {
    diagnosticPanel.classList.toggle('diagnostic-panel--collapsed', !isExpanded);
  }
}

function getMissingRequiredElementIds() {
  const requiredElements = [
    ['webcams-table-body', tableBody],
    ['webcam-form', webcamForm],
    ['form-title', formTitle],
    ['cancel-edit-btn', cancelEditBtn],
    ['refresh-webcams-btn', refreshBtn],
    ['editing-webcam-id', editingWebcamIdInput],
    ['webcam-transport', document.getElementById('webcam-transport')],
    ['copy-diagnostic-report-btn', copyDiagnosticReportBtn],
    ['management-main', managementMain],
    ['overview-view', overviewView],
    ['devices-view', devicesView],
    ['discovered-view', discoveredView],
    ['settings-view', settingsView],
    ['view-overview-btn', viewOverviewBtn],
    ['view-devices-btn', viewDevicesBtn],
    ['view-discovered-btn', viewDiscoveredBtn],
    ['view-settings-btn', viewSettingsBtn],
    ['theme-toggle-btn', themeToggleBtn],
  ];

  return requiredElements.filter(([, element]) => element == null).map(([id]) => id);
}

function isDiagnosticPanelContentVisible() {
  if (!(diagnosticsCollapsibleContainer instanceof HTMLElement)) {
    return false;
  }

  return (
    !diagnosticsCollapsibleContainer.hidden &&
    !diagnosticsCollapsibleContainer.classList.contains('hidden')
  );
}

function toggleDiagnosticPanelContent() {
  if (!(diagnosticsAdvancedCheckbox instanceof HTMLInputElement)) {
    return;
  }

  setDiagnosticPanelExpanded(diagnosticsAdvancedCheckbox.checked);
}

function updateBaseUrlValidation(transport = 'http') {
  const baseUrlInput = document.getElementById('webcam-base-url');
  if (!(baseUrlInput instanceof HTMLInputElement)) {
    return;
  }

  baseUrlInput.setCustomValidity('');

  if (transport === 'docker') {
    baseUrlInput.removeAttribute('type');
    baseUrlInput.setAttribute('pattern', DOCKER_BASE_URL_PATTERN);
    baseUrlInput.title = DOCKER_BASE_URL_HINT;
    return;
  }

  baseUrlInput.type = 'url';
  baseUrlInput.setAttribute('pattern', String.raw`https?://[^\s]+`);
  baseUrlInput.title = 'Must be a valid HTTP or HTTPS URL';
}

function formatDateTime(isoString) {
  if (!isoString) {
    return '—';
  }

  const parsed = new Date(isoString);
  if (Number.isNaN(parsed.getTime())) {
    return isoString;
  }

  return parsed.toLocaleString();
}

function getDiscoveryInfo(webcam = {}) {
  const discovery = webcam.discovery || {};
  const source = discovery.source || 'manual';
  const firstSeen = discovery.first_seen || webcam.last_seen || null;
  const lastAnnounceAt = discovery.last_announce_at || null;
  const approved = source === 'discovered' ? discovery.approved === true : true;
  return { source, firstSeen, lastAnnounceAt, approved };
}

function describeApiError(errorPayload = {}) {
  const code = errorPayload?.error?.code || errorPayload?.code;
  const details = errorPayload?.error?.details || errorPayload?.details || {};

  if (code === 'DISCOVERY_PRIVATE_IP_BLOCKED') {
    return `Discovery registration blocked by private-IP policy. ${details.remediation || 'Set MIO_ALLOW_PRIVATE_IPS=true only for trusted internal networks.'}`;
  }

  if (code === 'WEBCAM_UNAUTHORIZED') {
    return "Token/auth mismatch: the remote webcam rejected credentials. Update this node's bearer token to match MANAGEMENT_AUTH_TOKEN on the webcam node.";
  }

  if (code === 'SSRF_BLOCKED') {
    return 'Private-IP policy blocked this target. Use a docker network hostname, or explicitly enable MIO_ALLOW_PRIVATE_IPS=true on management for trusted internal networks.';
  }

  return errorPayload?.error?.message || errorPayload?.message || 'Request failed.';
}

function showFeedback(message, isError = false) {
  if (!(feedback instanceof HTMLElement)) {
    if (message) {
      const logger = isError ? console.error : console.info;
      logger(`[management-ui] ${message}`);
    }
    return;
  }
  feedback.textContent = message;
  feedback.style.color = isError ? '#b91c1c' : '#166534';
}

function getManagementBearerToken() {
  return managementApiBearerToken;
}

function syncManagementTokenInputs(token) {
  if (managementApiTokenInput instanceof HTMLInputElement) {
    managementApiTokenInput.value = token;
  }
  if (settingsManagementApiToken instanceof HTMLInputElement) {
    settingsManagementApiToken.value = token;
  }
}

function setManagementBearerToken(token, { persist = true } = {}) {
  const normalized = String(token || '').trim();
  managementApiBearerToken = normalized;
  syncManagementTokenInputs(normalized);

  if (!persist) {
    return;
  }

  try {
    if (normalized) {
      globalThis.localStorage?.setItem(API_TOKEN_STORAGE_KEY, normalized);
    } else {
      globalThis.localStorage?.removeItem(API_TOKEN_STORAGE_KEY);
    }
  } catch {
    // Ignore local storage failures.
  }
}

function initializeManagementBearerToken() {
  let storedToken = '';
  try {
    storedToken = globalThis.localStorage?.getItem(API_TOKEN_STORAGE_KEY) || '';
  } catch {
    // Ignore local storage failures.
  }

  const fallbackInputToken =
    managementApiTokenInput instanceof HTMLInputElement ? managementApiTokenInput.value.trim() : '';
  setManagementBearerToken(storedToken || fallbackInputToken, { persist: false });
}

function openUtilityPanel(title, htmlContent) {
  if (
    !(utilityPanel instanceof HTMLElement) ||
    !(utilityPanelTitle instanceof HTMLElement) ||
    !(utilityPanelContent instanceof HTMLElement)
  ) {
    return;
  }

  utilityPanelTitle.textContent = title;
  utilityPanelContent.innerHTML = htmlContent;
  utilityPanel.classList.remove('hidden');
}

function closeUtilityPanel() {
  if (!(utilityPanel instanceof HTMLElement)) {
    return;
  }
  utilityPanel.classList.add('hidden');
}

function openHelpPanel() {
  openUtilityPanel(
    'Connection Help',
    `
      <ul class="overview-list">
        <li>Use the dashboard token to authenticate management API requests.</li>
        <li>Use Diagnose on a node to inspect DNS, network, and API endpoint health.</li>
        <li>Discovery approvals activate announced nodes; reject keeps them pending.</li>
        <li>Private-IP and SSRF protections can block unsafe targets by policy.</li>
      </ul>
    `
  );
}

function openExportPanel() {
  if (!latestDiagnosticResult) {
    openUtilityPanel(
      'Export Diagnostic Report',
      '<p>No diagnostic report is available yet. Run <strong>Diagnose</strong> for any node first.</p>'
    );
    return;
  }

  const report = buildDiagnosticTextReport(latestDiagnosticResult);
  openUtilityPanel(
    'Export Diagnostic Report',
    `
      <p>Most recent diagnostic report is available below.</p>
      <pre class="utility-panel__report">${escapeHtml(report)}</pre>
    `
  );
}

/**
 * Fetch from management API with bearer token authentication.
 *
 * @async
 * @param {string} path - API endpoint path (e.g., "/api/webcams").
 * @param {Object} [options={}] - Fetch options (method, body, headers, etc.).
 * @returns {Promise<Response>} Fetch response.
 * @throws {Error} If response is 401, shows authentication error hint.
 */
async function managementFetch(path, options = {}) {
  const token = getManagementBearerToken();
  const authHeaders = token ? { Authorization: `Bearer ${token}` } : {};

  const response = await fetch(path, {
    ...options,
    headers: { ...options.headers, ...authHeaders },
  });

  if (response.status === 401) {
    const unauthorizedError = new Error(API_AUTH_HINT);
    unauthorizedError.isUnauthorized = true;
    unauthorizedError.response = response;
    throw unauthorizedError;
  }

  return response;
}

function getAuthPayload() {
  const type = document.getElementById('webcam-auth-type').value;

  if (type !== 'bearer') {
    return { type: 'none' };
  }

  const token = document.getElementById('webcam-auth-token').value.trim();
  return token ? { type, token } : { type };
}

function getParsedLabels() {
  const raw = document.getElementById('webcam-labels').value.trim();
  if (!raw) {
    return {};
  }
  return JSON.parse(raw);
}

function buildWebcamPayload({ preserveLastSeen = false } = {}) {
  const nowIso = new Date().toISOString();
  const capabilities = document
    .getElementById('webcam-capabilities')
    .value.split(',')
    .map((entry) => entry.trim())
    .filter(Boolean);

  const payload = {
    id: document.getElementById('webcam-id').value.trim(),
    name: document.getElementById('webcam-name').value.trim(),
    base_url: document.getElementById('webcam-base-url').value.trim(),
    transport: document.getElementById('webcam-transport').value,
    auth: getAuthPayload(),
    capabilities,
    labels: getParsedLabels(),
    last_seen: nowIso,
  };

  if (preserveLastSeen) {
    const existing = webcams.find((node) => node.id === editingWebcamIdInput.value);
    if (existing?.last_seen) {
      payload.last_seen = existing.last_seen;
    }
  }

  return payload;
}

function statusClass(statusText) {
  const normalized = (statusText || 'unknown').toLowerCase();
  if (['ok', 'healthy', 'ready'].includes(normalized)) {
    return 'ui-status-pill--success';
  }
  if (['error', 'down', 'failed', 'unhealthy'].includes(normalized)) {
    return 'ui-status-pill--error';
  }
  return 'ui-status-pill--neutral';
}

const STATUS_SUBTYPE_CONFIG = {
  unsupported_transport: {
    label: 'Unsupported transport',
    helpText: 'Configured transport is not supported by the target node.',
    statusClass: 'ui-status-pill--error',
  },
  unauthorized: {
    label: 'Unauthorized',
    helpText: 'Credentials were rejected by the webcam API.',
    statusClass: 'ui-status-pill--error',
  },
  no_response: {
    label: 'No response',
    helpText: 'Node did not return a valid status response.',
    statusClass: 'ui-status-pill--error',
  },
  partial_probe: {
    label: 'Partial probe',
    helpText: 'Node responded, but readiness or probe checks are incomplete.',
    statusClass: 'ui-status-pill--neutral',
  },
  degraded: {
    label: 'Degraded',
    helpText: 'Node is reachable but reports a degraded state.',
    statusClass: 'ui-status-pill--neutral',
  },
  healthy: {
    label: 'Healthy',
    helpText: 'Node is ready and healthy.',
    statusClass: 'ui-status-pill--success',
  },
};

function normalizeWebcamStatusError(error = {}) {
  return {
    status: 'error',
    stream_available: false,
    error_code: error.code || 'UNKNOWN_ERROR',
    error_message: error.message || 'Node status request failed.',
    error_details: error.details || null,
  };
}

function isFailureStatus(status = {}) {
  if (status.error_code) {
    return true;
  }

  const normalized = String(status.status || 'unknown').toLowerCase();
  return ['error', 'failed', 'down', 'unhealthy', 'unauthorized'].includes(normalized);
}

function enrichStatusWithAggregation(webcamId, status = {}) {
  const existing = webcamStatusAggregationMap.get(webcamId) || {
    last_success_at: null,
    first_failure_at: null,
    consecutive_failures: 0,
  };

  const next = {
    last_success_at: status.last_success_at || existing.last_success_at,
    first_failure_at: status.first_failure_at || existing.first_failure_at,
    consecutive_failures: Number.isFinite(status.consecutive_failures)
      ? status.consecutive_failures
      : existing.consecutive_failures,
  };

  const nowIso = new Date().toISOString();

  if (isFailureStatus(status)) {
    next.first_failure_at = next.first_failure_at || nowIso;
    next.consecutive_failures += 1;
  } else {
    next.last_success_at = next.last_success_at || nowIso;
    next.first_failure_at = null;
    next.consecutive_failures = 0;
  }

  webcamStatusAggregationMap.set(webcamId, next);
  return { ...status, ...next };
}

function formatAggregationDetails(status = {}) {
  const fragments = [];

  if (status.last_success_at) {
    fragments.push(`Last success: ${new Date(status.last_success_at).toLocaleString()}`);
  }

  if (status.first_failure_at) {
    fragments.push(`First failure: ${new Date(status.first_failure_at).toLocaleString()}`);
  }

  if (status.consecutive_failures > 0) {
    fragments.push(`Consecutive failures: ${status.consecutive_failures}`);
  }

  return fragments.join(' • ');
}

function getStatusReason(status = {}) {
  const code = status.error_code;
  const knownReasons = {
    SSRF_BLOCKED: {
      title: 'Private-IP policy blocked this webcam target.',
      hint: "Use a docker network hostname (e.g., 'motion-in-ocean-webcam:8000') or explicitly set MIO_ALLOW_PRIVATE_IPS=true on management for trusted internal networks. Click Diagnose for details.",
    },
    NETWORK_UNREACHABLE: {
      title: 'Node is unreachable on the network.',
      hint: 'Check webcam is running, network connectivity, and firewall rules. Click Diagnose for details.',
    },
    DOCKER_PROXY_UNREACHABLE: {
      title: 'Docker proxy is unreachable.',
      hint: 'Verify docker-socket-proxy is running and accessible on configured host and port. Click Diagnose for details.',
    },
    DOCKER_CONTAINER_NOT_FOUND: {
      title: 'Container not found on docker proxy.',
      hint: 'Verify the container ID/name is correct and running on the docker host.',
    },
    DOCKER_API_ERROR: {
      title: 'Docker API returned an error.',
      hint: 'Check docker proxy configuration and container status.',
    },
    INVALID_DOCKER_URL: {
      title: 'Docker URL is invalid.',
      hint: 'Use format: docker://proxy-hostname:port/container-id',
    },
    WEBCAM_UNREACHABLE: {
      title: 'Node is unreachable.',
      hint: 'Check the webcam base URL, networking, and that the webcam service is running.',
    },
    WEBCAM_UNAUTHORIZED: {
      title: 'Token/auth mismatch with remote node.',
      hint: 'Set this webcam bearer token to match the webcam webcam MANAGEMENT_AUTH_TOKEN, then refresh.',
    },
    WEBCAM_INVALID_RESPONSE: {
      title: 'Node returned an invalid response.',
      hint: 'Verify the webcam API version and status endpoint compatibility.',
    },
    TRANSPORT_UNSUPPORTED: {
      title: 'Configured transport is unsupported.',
      hint: 'Switch to a supported transport for this node.',
    },
    WEBCAM_API_MISMATCH: {
      title: 'Node API does not match expected management endpoints.',
      hint: 'Confirm the webcam is running the compatible management service and exposes /api/status.',
    },
  };

  if (code && knownReasons[code]) {
    const reason = knownReasons[code];
    return `${reason.title} ${reason.hint}`;
  }

  if (status.error_message) {
    return status.error_message;
  }

  return 'No additional details available.';
}

function normalizeWebcamStatusForUi(status = {}) {
  const statusText = String(status.status || 'unknown').toLowerCase();
  const errorCode = String(status.error_code || '').toUpperCase();
  const isReady = status.ready === true;

  let subtype = 'no_response';

  if (errorCode === 'TRANSPORT_UNSUPPORTED') {
    subtype = 'unsupported_transport';
  } else if (errorCode === 'WEBCAM_API_MISMATCH') {
    subtype = 'no_response';
  } else if (errorCode === 'WEBCAM_UNAUTHORIZED' || statusText === 'unauthorized') {
    subtype = 'unauthorized';
  } else if (statusText === 'ok' || statusText === 'healthy' || statusText === 'ready') {
    subtype = isReady ? 'healthy' : 'partial_probe';
  } else if (statusText === 'degraded' || statusText === 'warning') {
    subtype = 'degraded';
  } else if (statusText === 'partial' || statusText === 'probing') {
    subtype = 'partial_probe';
  } else if (statusText === 'error' || statusText === 'failed' || statusText === 'down') {
    subtype = 'no_response';
  }

  const config = STATUS_SUBTYPE_CONFIG[subtype] || {
    label: 'Unknown',
    helpText: 'Node state is unknown.',
    statusClass: statusClass(statusText),
  };

  let reasonText = getStatusReason(status);
  if (subtype === 'healthy') {
    reasonText = 'Ready and responding.';
  } else if (subtype === 'partial_probe') {
    reasonText = status.error_message || 'Node responded, but readiness is incomplete.';
  } else if (subtype === 'degraded') {
    reasonText = status.error_message || 'Node is reachable, but operating in a degraded mode.';
  }

  return {
    subtype,
    label: config.label,
    helpText: config.helpText,
    statusClass: config.statusClass,
    reasonText,
  };
}

function escapeHtml(value) {
  const div = document.createElement('div');
  div.textContent = value == null ? '' : String(value);
  return div.innerHTML;
}

function setTextContent(element, text) {
  if (element instanceof HTMLElement) {
    element.textContent = text;
  }
}

function getViewFromLocationHash() {
  const rawHash = String(globalThis.location?.hash || '').replace(VIEW_HASH_PREFIX, '');
  return VIEWS.includes(rawHash) ? rawHash : 'overview';
}

function setActiveView(view) {
  if (!VIEWS.includes(view)) {
    return;
  }
  const viewMap = {
    overview: overviewView,
    devices: devicesView,
    discovered: discoveredView,
    settings: settingsView,
  };
  for (const [name, element] of Object.entries(viewMap)) {
    if (element instanceof HTMLElement) {
      element.classList.toggle('hidden', name !== view);
    }
  }
  const btnMap = {
    overview: viewOverviewBtn,
    devices: viewDevicesBtn,
    discovered: viewDiscoveredBtn,
    settings: viewSettingsBtn,
  };
  for (const [name, button] of Object.entries(btnMap)) {
    if (button instanceof HTMLButtonElement) {
      const active = name === view;
      button.classList.toggle('management-view-btn--active', active);
      button.setAttribute('aria-current', active ? 'page' : 'false');
    }
  }
  const railBtnMap = {
    overview: [railOverviewBtn, mobileOverviewBtn],
    devices: [railDevicesBtn, mobileDevicesBtn],
    discovered: [railDiscoveredBtn, mobileDiscoveredBtn],
    settings: [railSettingsBtn, mobileSettingsBtn],
  };
  for (const [name, buttons] of Object.entries(railBtnMap)) {
    const active = name === view;
    for (const button of buttons) {
      if (button instanceof HTMLButtonElement) {
        button.classList.toggle('rail-btn--active', active);
        button.classList.toggle('mobile-rail-btn--active', active);
        button.setAttribute('aria-current', active ? 'page' : 'false');
      }
    }
  }
  if (globalThis.location?.hash !== `#${view}`) {
    globalThis.history.replaceState(null, '', `#${view}`);
  }
}

function applyTheme(theme) {
  const resolvedTheme = theme === 'dark' ? 'dark' : 'light';
  document.documentElement.setAttribute('data-theme', resolvedTheme);
  setTextContent(themeToggleBtn, resolvedTheme === 'dark' ? 'Light Theme' : 'Dark Theme');
  try {
    globalThis.localStorage?.setItem(THEME_STORAGE_KEY, resolvedTheme);
  } catch {
    // Ignore local storage failures.
  }
}

function initializeTheme() {
  let preferredTheme = 'light';
  try {
    preferredTheme = globalThis.localStorage?.getItem(THEME_STORAGE_KEY) || 'light';
  } catch {
    // Ignore local storage failures.
  }
  applyTheme(preferredTheme);
}

function getDiscoveredNodes() {
  return webcams.filter((node) => {
    const discovery = getDiscoveryInfo(node);
    return discovery.source === 'discovered' && !discovery.approved;
  });
}

function loadSnoozedDiscoveredIds() {
  try {
    const raw = globalThis.localStorage?.getItem(SNOOZE_STORAGE_KEY) || '[]';
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      discoveredSnoozedIds = new Set(parsed.filter((entry) => typeof entry === 'string'));
    }
  } catch {
    discoveredSnoozedIds = new Set();
  }
}

function persistSnoozedDiscoveredIds() {
  try {
    globalThis.localStorage?.setItem(
      SNOOZE_STORAGE_KEY,
      JSON.stringify(Array.from(discoveredSnoozedIds))
    );
  } catch {
    // Ignore local storage failures.
  }
}

function appendActivityFeed(message, level = 'info') {
  const timestamp = new Date().toISOString();
  activityFeed.unshift({ timestamp, message, level });
  if (activityFeed.length > 40) {
    activityFeed = activityFeed.slice(0, 40);
  }
}

function renderOverviewPanel() {
  if (overviewSnapshot) {
    setTextContent(overviewTotalWebcams, String(overviewSnapshot.total_webcams ?? 0));
    setTextContent(overviewHealthyWebcams, String(overviewSnapshot.healthy_webcams ?? 0));
    setTextContent(overviewUnavailableWebcams, String(overviewSnapshot.unavailable_webcams ?? 0));
    setTextContent(
      overviewStreamingWebcams,
      String(overviewSnapshot.stream_available_webcams ?? 0)
    );
  }

  if (overviewActivityList instanceof HTMLElement) {
    if (!activityFeed.length) {
      overviewActivityList.innerHTML = '<li>No activity yet.</li>';
    } else {
      overviewActivityList.innerHTML = activityFeed
        .map(
          (entry) =>
            `<li><strong>${escapeHtml(new Date(entry.timestamp).toLocaleTimeString())}</strong> ${escapeHtml(entry.message)}</li>`
        )
        .join('');
    }
  }

  if (overviewActionList instanceof HTMLElement) {
    const statusEntries = Array.from(webcamStatusMap.values());
    const authIssues = statusEntries.filter(
      (status) => String(status.error_code || '').toUpperCase() === 'WEBCAM_UNAUTHORIZED'
    ).length;
    const privateIpBlocked = statusEntries.filter(
      (status) => String(status.error_code || '').toUpperCase() === 'SSRF_BLOCKED'
    ).length;
    const pendingDiscovered = getDiscoveredNodes().length;
    const items = [];
    if (authIssues > 0) {
      items.push(`Auth remediation needed on ${authIssues} node(s).`);
    }
    if (pendingDiscovered > 0) {
      items.push(`${pendingDiscovered} discovered device(s) waiting for review.`);
    }
    if (privateIpBlocked > 0) {
      items.push(`${privateIpBlocked} node(s) blocked by safety rules.`);
    }
    overviewActionList.innerHTML = items.length
      ? items.map((item) => `<li>${escapeHtml(item)}</li>`).join('')
      : '<li>No action items.</li>';
  }
}

function renderDiscoveredPanel() {
  const pendingNodes = getDiscoveredNodes().filter((node) => !discoveredSnoozedIds.has(node.id));
  if (!selectedDiscoveredNodeId && pendingNodes.length > 0) {
    selectedDiscoveredNodeId = pendingNodes[0].id;
  }
  if (!pendingNodes.some((node) => node.id === selectedDiscoveredNodeId)) {
    selectedDiscoveredNodeId = pendingNodes[0]?.id || '';
  }

  if (discoveredList instanceof HTMLElement) {
    if (!pendingNodes.length) {
      discoveredList.innerHTML = '<li>No discovered devices pending approval.</li>';
    } else {
      discoveredList.innerHTML = pendingNodes
        .map((node) => {
          const selectedClass =
            node.id === selectedDiscoveredNodeId ? ' discovered-item--selected' : '';
          return `<li>
            <button class="discovered-item${selectedClass}" data-discovered-id="${escapeHtml(node.id)}" type="button">
              <strong>${escapeHtml(node.name || node.id)}</strong><br/>
              <small>${escapeHtml(node.base_url || 'Unknown URL')}</small>
            </button>
          </li>`;
        })
        .join('');
    }
  }

  if (discoveredNotes instanceof HTMLElement) {
    const activeStatus = selectedDiscoveredNodeId
      ? webcamStatusMap.get(selectedDiscoveredNodeId)
      : undefined;
    const notes = [];
    if (activeStatus?.error_message) {
      notes.push(activeStatus.error_message);
    }
    if (activeStatus?.error_details) {
      notes.push(String(activeStatus.error_details));
    }
    if (!notes.length) {
      notes.push('Blocked by local safety rule.');
    }
    discoveredNotes.innerHTML = notes.map((note) => `<li>${escapeHtml(note)}</li>`).join('');
  }

  const actionDisabled = !selectedDiscoveredNodeId;
  if (discoveredApproveBtn instanceof HTMLButtonElement) {
    discoveredApproveBtn.disabled = actionDisabled;
  }
  if (discoveredRejectBtn instanceof HTMLButtonElement) {
    discoveredRejectBtn.disabled = actionDisabled;
  }
  if (discoveredLaterBtn instanceof HTMLButtonElement) {
    discoveredLaterBtn.disabled = actionDisabled;
  }
}

async function fetchOverview() {
  try {
    const response = await managementFetch('/api/management/overview');
    if (!response.ok) {
      return;
    }
    const payload = await response.json();
    overviewSnapshot = payload.summary || null;
    renderOverviewPanel();
  } catch {
    // Non-fatal: overview panel can still render from current status maps.
  }
}

function setDiscoveredFeedback(message, isError = false) {
  if (!(discoveredFeedback instanceof HTMLElement)) {
    return;
  }
  discoveredFeedback.textContent = message;
  discoveredFeedback.style.color = isError ? '#b91c1c' : '#166534';
}

async function applyDiscoveredDecision(decision) {
  if (!selectedDiscoveredNodeId) {
    setDiscoveredFeedback('Select a discovered node first.', true);
    return;
  }
  if (decision === 'snooze') {
    discoveredSnoozedIds.add(selectedDiscoveredNodeId);
    persistSnoozedDiscoveredIds();
    setDiscoveredFeedback(`Node ${selectedDiscoveredNodeId} snoozed for this browser session.`);
    renderDiscoveredPanel();
    return;
  }
  const success = await setDiscoveryApproval(selectedDiscoveredNodeId, decision);
  if (success) {
    setDiscoveredFeedback(`Node ${selectedDiscoveredNodeId} ${decision}d.`);
  } else {
    setDiscoveredFeedback(`Could not ${decision} node ${selectedDiscoveredNodeId}.`, true);
  }
}

function setSettingsFeedback(message, isError = false) {
  if (!(settingsFeedback instanceof HTMLElement)) {
    return;
  }
  settingsFeedback.textContent = message;
  settingsFeedback.style.color = isError ? '#b91c1c' : '#166534';
}

function setSettingsTab(tabName) {
  const panels = {
    auth: settingsAuthPanel,
    discovery: settingsDiscoveryPanel,
    runtime: settingsRuntimePanel,
  };
  for (const [name, panel] of Object.entries(panels)) {
    if (panel instanceof HTMLElement) {
      panel.classList.toggle('hidden', name !== tabName);
    }
  }
  settingsTabButtons.forEach((button) => {
    if (!(button instanceof HTMLButtonElement)) {
      return;
    }
    const active = button.dataset.settingsTab === tabName;
    button.classList.toggle('management-view-btn--active', active);
    button.setAttribute('aria-current', active ? 'true' : 'false');
  });
}

function renderRuntimeSettingsChanges(changesPayload = {}) {
  const overridden = Array.isArray(changesPayload.overridden) ? changesPayload.overridden : [];
  if (settingsRuntimeSummary instanceof HTMLElement) {
    settingsRuntimeSummary.textContent =
      overridden.length > 0 ? 'Using custom values' : 'Using environment defaults';
  }
  if (settingsOverridesList instanceof HTMLElement) {
    settingsOverridesList.innerHTML = overridden.length
      ? overridden
          .map(
            (entry) =>
              `<li>${escapeHtml(entry.category || 'unknown')}.${escapeHtml(entry.key || 'unknown')} = ${escapeHtml(JSON.stringify(entry.value))}</li>`
          )
          .join('')
      : '<li>No overrides.</li>';
  }
}

async function fetchSettingsData() {
  try {
    const [settingsResponse, changesResponse] = await Promise.all([
      managementFetch('/api/settings'),
      managementFetch('/api/settings/changes'),
    ]);
    if (!settingsResponse.ok) {
      throw new Error('Could not load settings.');
    }
    currentSettingsPayload = await settingsResponse.json();
    const settingsDiscovery = currentSettingsPayload.discovery || {};
    if (settingsDiscoveryEnabled instanceof HTMLInputElement) {
      settingsDiscoveryEnabled.checked = Boolean(settingsDiscovery.discovery_enabled);
    }
    if (settingsDiscoveryUrl instanceof HTMLInputElement) {
      settingsDiscoveryUrl.value = String(settingsDiscovery.discovery_management_url || '');
    }
    if (settingsDiscoveryToken instanceof HTMLInputElement) {
      settingsDiscoveryToken.value = String(settingsDiscovery.discovery_token || '');
    }
    if (settingsDiscoveryInterval instanceof HTMLInputElement) {
      settingsDiscoveryInterval.value = String(settingsDiscovery.discovery_interval_seconds ?? 30);
    }
    if (changesResponse.ok) {
      const changesPayload = await changesResponse.json();
      renderRuntimeSettingsChanges(changesPayload);
    }
    if (settingsValidationSummary instanceof HTMLElement) {
      settingsValidationSummary.textContent = 'Validation summary';
    }
  } catch (error) {
    setSettingsFeedback(error?.message || 'Failed to load settings.', true);
  }
}

async function saveSettings() {
  if (settingsManagementApiToken instanceof HTMLInputElement) {
    setManagementBearerToken(settingsManagementApiToken.value);
  }

  if (
    !(settingsDiscoveryEnabled instanceof HTMLInputElement) ||
    !(settingsDiscoveryUrl instanceof HTMLInputElement) ||
    !(settingsDiscoveryToken instanceof HTMLInputElement) ||
    !(settingsDiscoveryInterval instanceof HTMLInputElement)
  ) {
    return;
  }
  setSettingsFeedback('');
  const patchPayload = {
    discovery: {
      discovery_enabled: settingsDiscoveryEnabled.checked,
      discovery_management_url: settingsDiscoveryUrl.value.trim(),
      discovery_token: settingsDiscoveryToken.value.trim(),
      discovery_interval_seconds: Number(settingsDiscoveryInterval.value || '30'),
    },
  };
  try {
    const response = await managementFetch('/api/settings', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patchPayload),
    });
    const payload = await response.json().catch(() => ({}));
    if (response.status === 422) {
      setSettingsFeedback('Saved. Some changes require restart to take effect.');
      if (settingsValidationSummary instanceof HTMLElement) {
        settingsValidationSummary.textContent = `Requires restart (${(payload.modified_on_restart || []).length})`;
      }
      await fetchSettingsData();
      return;
    }
    if (!response.ok) {
      setSettingsFeedback(describeApiError(payload) || 'Failed to save settings.', true);
      return;
    }
    setSettingsFeedback('Settings saved.');
    if (settingsValidationSummary instanceof HTMLElement) {
      settingsValidationSummary.textContent = 'Validation summary';
    }
    await fetchSettingsData();
  } catch (error) {
    setSettingsFeedback(error?.message || 'Failed to save settings.', true);
  }
}

async function resetSettings() {
  setSettingsFeedback('');
  try {
    const response = await managementFetch('/api/settings/reset', { method: 'POST' });
    if (!response.ok) {
      setSettingsFeedback('Reset failed.', true);
      return;
    }
    setSettingsFeedback('Settings reset to defaults.');
    await fetchSettingsData();
  } catch (error) {
    setSettingsFeedback(error?.message || 'Reset failed.', true);
  }
}

function renderRows() {
  if (!webcams.length) {
    tableBody.innerHTML = '<tr><td colspan="8" class="empty">No nodes registered.</td></tr>';
    return;
  }

  tableBody.innerHTML = webcams
    .map((node) => {
      const status = webcamStatusMap.get(node.id) || { status: 'unknown', stream_available: false };
      const normalizedStatus = normalizeWebcamStatusForUi(status);
      const streamText = status.stream_available ? 'Available' : 'Unavailable';
      const discovery = getDiscoveryInfo(node);
      const aggregateDetails = formatAggregationDetails(status);
      const detailsTooltip = [normalizedStatus.helpText, status.error_details]
        .filter(Boolean)
        .join(' ');
      const approvalHint =
        discovery.source === 'discovered' && !discovery.approved
          ? 'Pending approval before full activation.'
          : '';
      const detailsText = [approvalHint, normalizedStatus.reasonText].filter(Boolean).join(' ');
      return `
        <tr>
          <td><strong>${escapeHtml(node.name)}</strong><br><small>${escapeHtml(node.id)}</small></td>
          <td>${escapeHtml(node.base_url)}</td>
          <td>${escapeHtml(node.transport)}</td>
          <td>
            <small>
              Source: <strong>${escapeHtml(discovery.source)}</strong><br>
              First seen: ${escapeHtml(formatDateTime(discovery.firstSeen))}<br>
              Last announce: ${escapeHtml(formatDateTime(discovery.lastAnnounceAt))}<br>
              Approval: ${escapeHtml(discovery.approved ? 'approved' : 'pending')}
            </small>
          </td>
          <td>
            <span class="ui-status-pill ${normalizedStatus.statusClass}" title="${escapeHtml(normalizedStatus.helpText)}">${escapeHtml(normalizedStatus.label)}</span>
          </td>
          <td>
            <small title="${escapeHtml(detailsTooltip)}">${escapeHtml(detailsText)}</small>
            ${aggregateDetails ? `<br><small>${escapeHtml(aggregateDetails)}</small>` : ''}
          </td>
          <td>${streamText}</td>
          <td>
            <div class="row-actions">
              <button class="ui-btn ui-btn--secondary" data-action="edit" data-id="${escapeHtml(node.id)}">Edit</button>
              <button class="ui-btn ui-btn--secondary" data-action="diagnose" data-id="${escapeHtml(node.id)}">Diagnose</button>
              ${discovery.source === 'discovered' ? `<button class="ui-btn ui-btn--secondary" data-action="approve" data-id="${escapeHtml(node.id)}">Approve</button><button class="ui-btn ui-btn--secondary" data-action="reject" data-id="${escapeHtml(node.id)}">Reject</button>` : ''}
              <button class="ui-btn ui-btn--danger" data-action="delete" data-id="${escapeHtml(node.id)}">Remove</button>
            </div>
          </td>
        </tr>
      `;
    })
    .join('');
}

/**
 * Fetch all registered nodes from API and update UI.
 *
 * @async
 * @returns {Promise<void>}
 */
async function fetchWebcams() {
  try {
    const response = await managementFetch('/api/webcams');
    if (!response.ok) {
      throw new Error('Failed to load nodes');
    }
    const payload = await response.json();
    webcams = payload.webcams || payload.nodes || [];
    const activeNodeIds = new Set(webcams.map((node) => node.id));
    for (const nodeId of webcamStatusMap.keys()) {
      if (!activeNodeIds.has(nodeId)) {
        webcamStatusMap.delete(nodeId);
        webcamStatusAggregationMap.delete(nodeId);
        previousStatusByNode.delete(nodeId);
        discoveredSnoozedIds.delete(nodeId);
      }
    }
    persistSnoozedDiscoveredIds();
    renderRows();
    renderDiscoveredPanel();
    renderOverviewPanel();
  } catch (error) {
    if (error?.isUnauthorized) {
      showFeedback(API_AUTH_HINT, true);
    } else {
      showFeedback(error.message || 'Failed to load nodes', true);
    }
    throw error;
  }
}

function startStatusRefreshInterval() {
  if (!statusRefreshIntervalId) {
    statusRefreshIntervalId = window.setInterval(() => {
      refreshStatuses({ fromInterval: true });
    }, 5000);
  }
}

function stopStatusRefreshInterval() {
  if (statusRefreshIntervalId) {
    window.clearInterval(statusRefreshIntervalId);
    statusRefreshIntervalId = undefined;
  }
}

async function refreshStatuses({ fromInterval = false } = {}) {
  const statusHistoryMap =
    typeof previousStatusByNode !== 'undefined' && previousStatusByNode instanceof Map
      ? previousStatusByNode
      : new Map();

  if (statusRefreshInFlight) {
    statusRefreshPending = true;
    if (!fromInterval) {
      statusRefreshPendingManual = true;
    }
    return;
  }

  statusRefreshInFlight = true;
  let allowManualFeedback = !fromInterval;
  let showedUnauthorizedFeedback = false;
  try {
    do {
      statusRefreshPending = false;
      allowManualFeedback = statusRefreshPendingManual;
      statusRefreshPendingManual = false;
      showedUnauthorizedFeedback = false;

      const currentToken = ++statusRefreshToken;
      const nextStatusMap = new Map();

      await Promise.all(
        webcams.map(async (node) => {
          try {
            const response = await managementFetch(
              `/api/webcams/${encodeURIComponent(node.id)}/status`
            );
            if (!response.ok) {
              let errorPayload = {};
              try {
                const parsed = await response.json();
                errorPayload = parsed?.error || parsed || {};
              } catch {
                errorPayload = {};
              }
              nextStatusMap.set(
                node.id,
                enrichStatusWithAggregation(node.id, normalizeWebcamStatusError(errorPayload))
              );
              return;
            }
            const payload = await response.json();
            nextStatusMap.set(node.id, enrichStatusWithAggregation(node.id, payload));
          } catch (error) {
            if (allowManualFeedback && error?.isUnauthorized && !showedUnauthorizedFeedback) {
              showFeedback(API_AUTH_HINT, true);
              showedUnauthorizedFeedback = true;
            }
            nextStatusMap.set(
              node.id,
              enrichStatusWithAggregation(
                node.id,
                normalizeWebcamStatusError({
                  message: error?.message || 'Failed to refresh webcam status.',
                })
              )
            );
          }
        })
      );

      if (currentToken === statusRefreshToken) {
        for (const [nodeId, nextStatus] of nextStatusMap.entries()) {
          const previous = statusHistoryMap.get(nodeId);
          const nextCode = String(nextStatus.error_code || '').toUpperCase();
          const nextState = String(nextStatus.status || 'unknown').toLowerCase();
          const prevCode = String(previous?.error_code || '').toUpperCase();
          const prevState = String(previous?.status || 'unknown').toLowerCase();

          if (!previous) {
            if (typeof appendActivityFeed === 'function') {
              appendActivityFeed(`${nodeId} status initialized: ${nextState}.`);
            }
          } else if (
            (prevCode !== nextCode && nextCode) ||
            (prevState !== nextState && nextState !== 'unknown')
          ) {
            const detail = nextCode || nextState;
            if (typeof appendActivityFeed === 'function') {
              appendActivityFeed(`${nodeId} status changed to ${detail}.`);
            }
          }

          if (previous && String(previous.error_code || '').toUpperCase() && !nextCode) {
            if (typeof appendActivityFeed === 'function') {
              appendActivityFeed(`${nodeId} recovered.`, 'success');
            }
          }
          statusHistoryMap.set(nodeId, nextStatus);
        }

        webcamStatusMap = nextStatusMap;
        if (typeof renderRows === 'function') {
          renderRows();
        }
        if (typeof renderDiscoveredPanel === 'function') {
          renderDiscoveredPanel();
        }
        if (typeof renderOverviewPanel === 'function') {
          renderOverviewPanel();
        }
      }
    } while (statusRefreshPending);
  } finally {
    statusRefreshInFlight = false;
  }
}

function resetForm() {
  webcamForm.reset();
  updateBaseUrlValidation(document.getElementById('webcam-transport').value);
  editingWebcamIdInput.value = '';
  formTitle.textContent = 'Add node';
  document.getElementById('webcam-id').disabled = false;
  cancelEditBtn.classList.add('hidden');
}

function setNodeFormPanelCollapsed(isCollapsed) {
  const isExpanded = !isCollapsed;

  if (
    !(toggleWebcamFormPanelBtn instanceof HTMLButtonElement) ||
    !(webcamFormContent instanceof HTMLElement)
  ) {
    return;
  }

  if (managementLayout instanceof HTMLElement) {
    managementLayout.classList.toggle('is-form-collapsed', isCollapsed);
  }

  if (webcamFormPanelContainer instanceof HTMLElement) {
    webcamFormPanelContainer.classList.toggle('is-form-collapsed', isCollapsed);
  }

  if (webcamFormContentWrapper instanceof HTMLElement) {
    webcamFormContentWrapper.classList.toggle('hidden', isCollapsed);
  }

  webcamFormContent.classList.toggle('hidden', isCollapsed);
  toggleWebcamFormPanelBtn.setAttribute('aria-expanded', String(isExpanded));
  toggleWebcamFormPanelBtn.textContent = isExpanded ? '«' : '»';
  toggleWebcamFormPanelBtn.title = isExpanded
    ? 'Collapse webcam form panel'
    : 'Expand webcam form panel';
  toggleWebcamFormPanelBtn.setAttribute(
    'aria-label',
    isExpanded ? 'Collapse webcam form panel' : 'Expand webcam form panel'
  );

  try {
    globalThis.localStorage?.setItem(NODE_FORM_COLLAPSED_STORAGE_KEY, String(isCollapsed));
  } catch {
    // Ignore storage failures in private/incognito environments.
  }
}

function toggleNodeFormPanel() {
  if (!(toggleWebcamFormPanelBtn instanceof HTMLButtonElement)) {
    return;
  }

  const isExpanded = toggleWebcamFormPanelBtn.getAttribute('aria-expanded') === 'true';
  setNodeFormPanelCollapsed(isExpanded);
}

function getStoredNodeFormCollapsedPreference() {
  try {
    return globalThis.localStorage?.getItem(NODE_FORM_COLLAPSED_STORAGE_KEY) === 'true';
  } catch {
    return false;
  }
}

/**
 * Submit webcam form (create or update).
 *
 * @async
 * @param {Event} event - Form submission event.
 * @returns {Promise<void>}
 */
async function submitNodeForm(event) {
  event.preventDefault();
  showFeedback('');

  const editingNodeId = editingWebcamIdInput.value;
  const isEdit = Boolean(editingNodeId);

  let payload;
  try {
    payload = buildWebcamPayload({ preserveLastSeen: isEdit });
  } catch {
    showFeedback('Labels must be valid JSON.', true);
    return;
  }

  const endpoint = isEdit ? `/api/webcams/${encodeURIComponent(editingNodeId)}` : '/api/webcams';
  const method = isEdit ? 'PUT' : 'POST';

  try {
    const response = await managementFetch(endpoint, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorPayload = await response.json().catch(() => ({}));
      showFeedback(describeApiError(errorPayload), true);
      return;
    }

    showFeedback(isEdit ? 'Node updated.' : 'Node added.');
    resetForm();
    await fetchWebcams();
    await refreshStatuses();
    await fetchOverview();
  } catch (error) {
    if (error?.isUnauthorized) {
      showFeedback(API_AUTH_HINT, true);
      return;
    }
    showFeedback(error.message || 'Network error occurred.', true);
  }
}

/**
 * Begin editing a webcam by loading it into the form.
 *
 * @param {string} nodeId - Node to edit.
 * @returns {void}
 */
function beginEditNode(nodeId) {
  const webcam = webcams.find((entry) => entry.id === nodeId);
  if (!webcam) {
    return;
  }

  editingWebcamIdInput.value = webcam.id;
  formTitle.textContent = `Edit webcam: ${webcam.id}`;
  document.getElementById('webcam-id').value = webcam.id;
  document.getElementById('webcam-id').disabled = true;
  document.getElementById('webcam-name').value = webcam.name || '';
  document.getElementById('webcam-base-url').value = webcam.base_url || '';
  document.getElementById('webcam-transport').value = webcam.transport || 'http';
  updateBaseUrlValidation(document.getElementById('webcam-transport').value);
  document.getElementById('webcam-auth-type').value = webcam.auth?.type || 'none';
  document.getElementById('webcam-auth-token').value = webcam.auth?.token || '';
  document.getElementById('webcam-capabilities').value = (webcam.capabilities || []).join(', ');
  document.getElementById('webcam-labels').value = JSON.stringify(webcam.labels || {}, null, 2);
  cancelEditBtn.classList.remove('hidden');
}

/**
 * Fetch and display diagnostic results for a node.
 *
 * @async
 * @param {string} nodeId - Node ID to diagnose.
 * @returns {Promise<void>}
 */
async function diagnoseNode(nodeId) {
  try {
    const response = await managementFetch(`/api/webcams/${encodeURIComponent(nodeId)}/diagnose`);
    if (!response.ok) {
      const errorPayload = await response.json().catch(() => ({}));
      showFeedback(errorPayload?.error?.message || 'Diagnostic request failed', true);
      return;
    }

    const diagnosticResult = await response.json();
    showDiagnosticResults(diagnosticResult);
  } catch (error) {
    if (error?.isUnauthorized) {
      showFeedback(API_AUTH_HINT, true);
      return;
    }
    showFeedback(error.message || 'Network error occurred.', true);
  }
}

function getDiagnosticCheckRows(diagnostics = {}) {
  const resolveState = (structuredStatus, fallbackState) => {
    const normalized = String(structuredStatus || '').toLowerCase();
    return ['pass', 'warn', 'fail'].includes(normalized) ? normalized : fallbackState;
  };

  return [
    {
      key: 'Registration',
      state: resolveState(
        diagnostics.registration?.status,
        diagnostics.registration?.valid ? 'pass' : 'fail'
      ),
      detail: diagnostics.registration?.valid
        ? 'Node registration is valid.'
        : diagnostics.registration?.error || 'Registration data is invalid.',
      meta: diagnostics.registration?.code ? `Code: ${diagnostics.registration.code}` : '',
    },
    {
      key: 'URL validation',
      state: resolveState(
        diagnostics.url_validation?.status,
        diagnostics.url_validation?.blocked ? 'fail' : 'pass'
      ),
      detail: diagnostics.url_validation?.blocked
        ? diagnostics.url_validation?.blocked_reason || 'URL blocked by policy.'
        : 'Base URL passed validation.',
      meta: diagnostics.url_validation?.code ? `Code: ${diagnostics.url_validation.code}` : '',
    },
    {
      key: 'DNS resolution',
      state: resolveState(
        diagnostics.dns_resolution?.status,
        diagnostics.dns_resolution?.resolves ? 'pass' : 'fail'
      ),
      detail: diagnostics.dns_resolution?.resolves
        ? 'DNS lookup succeeded.'
        : diagnostics.dns_resolution?.error || 'DNS lookup failed.',
      meta:
        diagnostics.dns_resolution?.resolved_ips?.length > 0
          ? `IPs: ${diagnostics.dns_resolution.resolved_ips.join(', ')}`
          : '',
    },
    {
      key: 'Network connectivity',
      state: resolveState(
        diagnostics.network_connectivity?.status,
        diagnostics.network_connectivity?.reachable ? 'pass' : 'fail'
      ),
      detail: diagnostics.network_connectivity?.reachable
        ? 'Node is reachable over the network.'
        : diagnostics.network_connectivity?.error || 'Could not reach node.',
      meta: [
        diagnostics.network_connectivity?.category
          ? `Category: ${diagnostics.network_connectivity.category}`
          : '',
        diagnostics.network_connectivity?.code
          ? `Code: ${diagnostics.network_connectivity.code}`
          : '',
      ]
        .filter(Boolean)
        .join(' · '),
    },
    {
      key: 'API endpoint',
      state: resolveState(
        diagnostics.api_endpoint?.status,
        diagnostics.api_endpoint?.accessible === false
          ? 'fail'
          : diagnostics.api_endpoint?.healthy === false
            ? 'warn'
            : 'pass'
      ),
      detail: diagnostics.api_endpoint?.status_code
        ? `HTTP ${diagnostics.api_endpoint.status_code}`
        : diagnostics.api_endpoint?.error || 'Endpoint check incomplete.',
      meta: [
        diagnostics.api_endpoint?.healthy === false && diagnostics.api_endpoint?.status_code === 503
          ? 'Node reachable but may still be initializing.'
          : '',
        diagnostics.api_endpoint?.code ? `Code: ${diagnostics.api_endpoint.code}` : '',
      ]
        .filter(Boolean)
        .join(' · '),
    },
  ];
}

function getDiagnosticSummaryState(checkRows = []) {
  const hasFail = checkRows.some((row) => row.state === 'fail');
  if (hasFail) {
    return { label: 'Action required', className: 'diagnostic-pill--fail', state: 'fail' };
  }

  const warningRows = checkRows.filter((row) => row.state === 'warn');
  if (warningRows.length > 0) {
    const transientWarningKeys = new Set(['API endpoint']);
    const onlyTransientWarnings = warningRows.every((row) => transientWarningKeys.has(row.key));
    if (onlyTransientWarnings) {
      return { label: 'Warning', className: 'diagnostic-pill--warn', state: 'warn' };
    }
    return { label: 'Action recommended', className: 'diagnostic-pill--warn', state: 'warn' };
  }

  return { label: 'Healthy', className: 'diagnostic-pill--pass', state: 'pass' };
}

function getConnectivityRemediation(category, diagnostics = {}) {
  const code = diagnostics.network_connectivity?.code || diagnostics.url_validation?.code || '';
  const codeText = code ? ` (${code})` : '';
  const categoryMap = {
    timeout: `Node connection timed out${codeText}. Retry in 30s while the service finishes startup.`,
    tls: `TLS handshake failed${codeText}. Verify certificates or switch the webcam base URL to http:// if TLS is not configured.`,
    dns: `Hostname could not be resolved${codeText}. Check the webcam base URL hostname and DNS configuration.`,
    connection_refused_or_reset: `Connection was refused${codeText}. Confirm the webcam process is running and listening on the configured port.`,
    network: `Network path is blocked${codeText}. Check firewall, routing, and container network settings.`,
    ssrf_blocked: `SSRF protection blocked this target${codeText}. Use an allowed hostname or update private-IP policy for trusted networks.`,
  };

  if (categoryMap[category]) {
    return categoryMap[category];
  }

  if (code === 'SSRF_BLOCKED') {
    return `SSRF protection blocked this target${codeText}. Update webcam base URL to an allowed address or relax policy for trusted private networks.`;
  }

  return 'Review check details below to resolve connectivity issues.';
}

function getDiagnosticSummaryBanner(summary, checkRows = [], diagnostics = {}) {
  if (summary.state === 'pass') {
    return {
      interpretation: 'All diagnostic checks passed; this webcam appears healthy and reachable.',
      cta: 'No action needed',
    };
  }

  const apiWarning = checkRows.find((row) => row.key === 'API endpoint' && row.state === 'warn');
  if (summary.state === 'warn' && apiWarning) {
    return {
      interpretation: 'Connectivity looks good, but the webcam API is still warming up.',
      cta: 'Retry in 30s',
    };
  }

  if (diagnostics.url_validation?.code === 'SSRF_BLOCKED') {
    return {
      interpretation: getConnectivityRemediation('ssrf_blocked', diagnostics),
      cta: 'Update webcam base URL',
    };
  }

  if (
    diagnostics.network_connectivity?.category === 'tls' ||
    diagnostics.network_connectivity?.category === 'dns' ||
    diagnostics.network_connectivity?.category === 'timeout' ||
    diagnostics.network_connectivity?.category === 'connection_refused_or_reset' ||
    diagnostics.network_connectivity?.category === 'network'
  ) {
    return {
      interpretation: getConnectivityRemediation(
        diagnostics.network_connectivity.category,
        diagnostics
      ),
      cta:
        diagnostics.network_connectivity.category === 'timeout'
          ? 'Retry in 30s'
          : 'Update webcam base URL',
    };
  }

  if (diagnostics.registration?.code === 'WEBCAM_UNAUTHORIZED') {
    return {
      interpretation:
        "Node authentication failed. The configured token does not match the node's expected credentials.",
      cta: 'Set auth token',
    };
  }

  return {
    interpretation:
      'One or more checks need remediation before this webcam can be considered healthy.',
    cta: 'Review recommendations',
  };
}

function renderDiagnosticRecommendations(guidance = [], recommendations = []) {
  const structured = recommendations.length
    ? recommendations
    : guidance.map((item) => ({ message: item, status: 'warn' }));

  const recommendationsList = structured.length
    ? structured
        .map((item) => {
          const state = ['pass', 'warn', 'fail'].includes(item.status) ? item.status : 'warn';
          const icon = state === 'pass' ? '[PASS]' : state === 'warn' ? '[WARN]' : '[FAIL]';
          const codeSuffix = item.code ? ` <small>(Code: ${escapeHtml(item.code)})</small>` : '';
          return `<li><span class="diagnostic-pill diagnostic-pill--${state}">${icon}</span> ${escapeHtml(item.message || '')}${codeSuffix}</li>`;
        })
        .join('')
    : '<li>No recommendations provided.</li>';

  diagnosticRecommendations.innerHTML = `
    <h4>Recommendations</h4>
    <ul>${recommendationsList}</ul>
  `;
}

function buildDiagnosticTextReport(diagnosticResult) {
  const nodeId = diagnosticResult.node_id || 'unknown';
  const diagnostics = diagnosticResult.diagnostics || {};
  const guidance = diagnosticResult.guidance || [];
  const recommendations = diagnosticResult.recommendations || [];
  const checkRows = getDiagnosticCheckRows(diagnostics);
  const summary = getDiagnosticSummaryState(checkRows);

  let output = `Diagnostic Report\nNode: ${nodeId}\nSummary: ${summary.label}\n\nChecks:\n`;

  checkRows.forEach((row) => {
    const icon = row.state === 'pass' ? '[PASS]' : row.state === 'warn' ? '[WARN]' : '[FAIL]';
    output += `${icon} ${row.key}: ${row.detail}${row.meta ? ` (${row.meta})` : ''}\n`;
  });

  output += '\nRecommendations:\n';
  const reportRecommendations = recommendations.length
    ? recommendations
    : guidance.map((item) => ({ message: item, status: 'warn' }));

  if (reportRecommendations.length === 0) {
    output += '- No recommendations provided.\n';
  } else {
    reportRecommendations.forEach((item) => {
      const icon = item.status === 'pass' ? '[PASS]' : item.status === 'fail' ? '[FAIL]' : '[WARN]';
      output += `- ${icon} ${item.message}${item.code ? ` (Code: ${item.code})` : ''}\n`;
    });
  }

  return output;
}

function showDiagnosticResults(diagnosticResult) {
  latestDiagnosticResult = diagnosticResult;
  const nodeId = diagnosticResult.node_id || 'unknown';
  const diagnostics = diagnosticResult.diagnostics || {};
  const checkRows = getDiagnosticCheckRows(diagnostics);
  const summary = getDiagnosticSummaryState(checkRows);
  const banner = getDiagnosticSummaryBanner(summary, checkRows, diagnostics);

  diagnosticWebcamId.textContent = nodeId;
  diagnosticContext.textContent = `Generated at ${new Date().toLocaleString()}`;
  diagnosticSummaryBadge.className = `diagnostic-pill ${summary.className}`;
  diagnosticSummaryBadge.textContent = summary.label;
  if (diagnosticOverallStatePill) {
    diagnosticOverallStatePill.className = `diagnostic-pill ${summary.className}`;
    diagnosticOverallStatePill.textContent = summary.label;
  }
  if (diagnosticSummaryInterpretation) {
    diagnosticSummaryInterpretation.textContent = banner.interpretation;
  }
  if (diagnosticSummaryCta) {
    diagnosticSummaryCta.textContent = banner.cta;
  }

  diagnosticChecksGrid.innerHTML = checkRows
    .map(
      (row) => `
        <article class="diagnostic-check-card">
          <div class="diagnostic-check-card__head">
            <h4>${escapeHtml(row.key)}</h4>
            <span class="diagnostic-pill diagnostic-pill--${escapeHtml(row.state)}">${escapeHtml(
              row.state.toUpperCase()
            )}</span>
          </div>
          <p>${escapeHtml(row.detail)}</p>
          ${row.meta ? `<small>${escapeHtml(row.meta)}</small>` : ''}
        </article>
      `
    )
    .join('');

  renderDiagnosticRecommendations(
    diagnosticResult.guidance || [],
    diagnosticResult.recommendations || []
  );
  copyDiagnosticReportBtn.disabled = false;
  setDiagnosticPanelExpanded(true);
  if (
    isDiagnosticPanelContentVisible() &&
    diagnosticPanel &&
    typeof diagnosticPanel.focus === 'function'
  ) {
    diagnosticPanel.focus();
  }
}

/**
 * Approve or reject a discovered node.
 *
 * @async
 * @param {string} nodeId - Node to approve or reject.
 * @param {string} decision - "approve" or "reject".
 * @returns {Promise<void>}
 */
async function setDiscoveryApproval(nodeId, decision) {
  try {
    const response = await managementFetch(
      `/api/webcams/${encodeURIComponent(nodeId)}/discovery/${decision}`,
      {
        method: 'POST',
      }
    );

    if (!response.ok) {
      const errorPayload = await response.json().catch(() => ({}));
      showFeedback(describeApiError(errorPayload), true);
      return false;
    }

    discoveredSnoozedIds.delete(nodeId);
    persistSnoozedDiscoveredIds();
    showFeedback(`Node ${nodeId} ${decision}d.`);
    await fetchWebcams();
    await refreshStatuses();
    await fetchOverview();
    return true;
  } catch (error) {
    if (error?.isUnauthorized) {
      showFeedback(API_AUTH_HINT, true);
      return false;
    }
    showFeedback(error.message || 'Network error occurred.', true);
    return false;
  }
}

async function removeNode(nodeId) {
  if (!window.confirm(`Delete webcam ${nodeId}?`)) {
    return;
  }

  try {
    const response = await managementFetch(`/api/webcams/${encodeURIComponent(nodeId)}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      const errorPayload = await response.json().catch(() => ({}));
      showFeedback(errorPayload?.error?.message || 'Delete failed', true);
      return;
    }

    showFeedback(`Node ${nodeId} removed.`);
    if (editingWebcamIdInput.value === nodeId) {
      resetForm();
    }
    await fetchWebcams();
    await refreshStatuses();
    await fetchOverview();
  } catch (error) {
    if (error?.isUnauthorized) {
      showFeedback(API_AUTH_HINT, true);
      return;
    }
    showFeedback(error.message || 'Network error occurred.', true);
  }
}

function onTableClick(event) {
  const target = event.target;
  if (!(target instanceof HTMLElement)) {
    return;
  }
  const action = target.dataset.action;
  const nodeId = target.dataset.id;

  if (!action || !nodeId) {
    return;
  }

  if (action === 'edit') {
    beginEditNode(nodeId);
  } else if (action === 'delete') {
    removeNode(nodeId);
  } else if (action === 'diagnose') {
    diagnoseNode(nodeId);
  } else if (action === 'approve') {
    setDiscoveryApproval(nodeId, 'approve');
  } else if (action === 'reject') {
    setDiscoveryApproval(nodeId, 'reject');
  }
}

async function init() {
  const missingElementIds = getMissingRequiredElementIds();
  if (missingElementIds.length > 0) {
    const details = `Missing required management UI element(s): ${missingElementIds.join(', ')}`;
    console.error(`[management-ui] ${details}`);
    showFeedback('Management UI failed to initialize due to missing page elements.', true);
    return;
  }

  webcamForm.addEventListener('submit', submitNodeForm);
  cancelEditBtn.addEventListener('click', () => {
    resetForm();
    showFeedback('');
  });
  if (typeof initializeTheme === 'function') {
    initializeTheme();
  }
  if (typeof initializeManagementBearerToken === 'function') {
    initializeManagementBearerToken();
  }
  if (typeof loadSnoozedDiscoveredIds === 'function') {
    loadSnoozedDiscoveredIds();
  }

  if (
    typeof managementApiTokenInput !== 'undefined' &&
    managementApiTokenInput instanceof HTMLInputElement
  ) {
    managementApiTokenInput.addEventListener('input', () => {
      setManagementBearerToken(managementApiTokenInput.value);
    });
  }
  if (
    typeof settingsManagementApiToken !== 'undefined' &&
    settingsManagementApiToken instanceof HTMLInputElement
  ) {
    settingsManagementApiToken.addEventListener('input', () => {
      setManagementBearerToken(settingsManagementApiToken.value);
    });
  }

  if (typeof viewOverviewBtn !== 'undefined' && viewOverviewBtn instanceof HTMLButtonElement) {
    viewOverviewBtn.addEventListener('click', () => setActiveView('overview'));
  }
  if (typeof viewDevicesBtn !== 'undefined' && viewDevicesBtn instanceof HTMLButtonElement) {
    viewDevicesBtn.addEventListener('click', () => setActiveView('devices'));
  }
  if (typeof viewDiscoveredBtn !== 'undefined' && viewDiscoveredBtn instanceof HTMLButtonElement) {
    viewDiscoveredBtn.addEventListener('click', () => setActiveView('discovered'));
  }
  if (typeof viewSettingsBtn !== 'undefined' && viewSettingsBtn instanceof HTMLButtonElement) {
    viewSettingsBtn.addEventListener('click', () => setActiveView('settings'));
  }
  if (typeof railOverviewBtn !== 'undefined' && railOverviewBtn instanceof HTMLButtonElement) {
    railOverviewBtn.addEventListener('click', () => setActiveView('overview'));
  }
  if (typeof railDevicesBtn !== 'undefined' && railDevicesBtn instanceof HTMLButtonElement) {
    railDevicesBtn.addEventListener('click', () => setActiveView('devices'));
  }
  if (typeof railDiscoveredBtn !== 'undefined' && railDiscoveredBtn instanceof HTMLButtonElement) {
    railDiscoveredBtn.addEventListener('click', () => setActiveView('discovered'));
  }
  if (typeof railSettingsBtn !== 'undefined' && railSettingsBtn instanceof HTMLButtonElement) {
    railSettingsBtn.addEventListener('click', () => setActiveView('settings'));
  }
  if (typeof mobileOverviewBtn !== 'undefined' && mobileOverviewBtn instanceof HTMLButtonElement) {
    mobileOverviewBtn.addEventListener('click', () => setActiveView('overview'));
  }
  if (typeof mobileDevicesBtn !== 'undefined' && mobileDevicesBtn instanceof HTMLButtonElement) {
    mobileDevicesBtn.addEventListener('click', () => setActiveView('devices'));
  }
  if (
    typeof mobileDiscoveredBtn !== 'undefined' &&
    mobileDiscoveredBtn instanceof HTMLButtonElement
  ) {
    mobileDiscoveredBtn.addEventListener('click', () => setActiveView('discovered'));
  }
  if (typeof mobileSettingsBtn !== 'undefined' && mobileSettingsBtn instanceof HTMLButtonElement) {
    mobileSettingsBtn.addEventListener('click', () => setActiveView('settings'));
  }
  if (typeof railHelpBtn !== 'undefined' && railHelpBtn instanceof HTMLButtonElement) {
    railHelpBtn.addEventListener('click', openHelpPanel);
  }
  if (typeof mobileHelpBtn !== 'undefined' && mobileHelpBtn instanceof HTMLButtonElement) {
    mobileHelpBtn.addEventListener('click', openHelpPanel);
  }
  if (typeof railExportBtn !== 'undefined' && railExportBtn instanceof HTMLButtonElement) {
    railExportBtn.addEventListener('click', openExportPanel);
  }
  if (typeof mobileExportBtn !== 'undefined' && mobileExportBtn instanceof HTMLButtonElement) {
    mobileExportBtn.addEventListener('click', openExportPanel);
  }
  if (
    typeof utilityPanelCloseBtn !== 'undefined' &&
    utilityPanelCloseBtn instanceof HTMLButtonElement
  ) {
    utilityPanelCloseBtn.addEventListener('click', closeUtilityPanel);
  }
  if (typeof themeToggleBtn !== 'undefined' && themeToggleBtn instanceof HTMLButtonElement) {
    themeToggleBtn.addEventListener('click', () => {
      const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
      applyTheme(currentTheme === 'dark' ? 'light' : 'dark');
    });
  }
  if (typeof globalThis.addEventListener === 'function') {
    globalThis.addEventListener('hashchange', () => {
      if (typeof setActiveView === 'function' && typeof getViewFromLocationHash === 'function') {
        setActiveView(getViewFromLocationHash());
      }
    });
  }

  refreshBtn.addEventListener('click', async () => {
    stopStatusRefreshInterval();
    try {
      await fetchWebcams();
      await refreshStatuses();
      await fetchOverview();
      showFeedback('Node list refreshed.');
    } finally {
      startStatusRefreshInterval();
    }
  });
  if (
    typeof refreshDashboardBtn !== 'undefined' &&
    refreshDashboardBtn instanceof HTMLButtonElement
  ) {
    refreshDashboardBtn.addEventListener('click', async () => {
      await fetchWebcams();
      await refreshStatuses();
      await fetchOverview();
      renderOverviewPanel();
    });
  }
  if (typeof scanDiscoveredBtn !== 'undefined' && scanDiscoveredBtn instanceof HTMLButtonElement) {
    scanDiscoveredBtn.addEventListener('click', async () => {
      await fetchWebcams();
      await refreshStatuses();
      await fetchOverview();
      renderDiscoveredPanel();
      setDiscoveredFeedback('Discovery queue refreshed.');
    });
  }
  if (typeof discoveredList !== 'undefined' && discoveredList instanceof HTMLElement) {
    discoveredList.addEventListener('click', (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) {
        return;
      }
      const button = target.closest('[data-discovered-id]');
      if (!(button instanceof HTMLElement)) {
        return;
      }
      const nodeId = button.dataset.discoveredId;
      if (!nodeId) {
        return;
      }
      selectedDiscoveredNodeId = nodeId;
      renderDiscoveredPanel();
    });
  }
  if (
    typeof discoveredApproveBtn !== 'undefined' &&
    discoveredApproveBtn instanceof HTMLButtonElement
  ) {
    discoveredApproveBtn.addEventListener('click', async () => {
      await applyDiscoveredDecision('approve');
      await fetchOverview();
    });
  }
  if (
    typeof discoveredRejectBtn !== 'undefined' &&
    discoveredRejectBtn instanceof HTMLButtonElement
  ) {
    discoveredRejectBtn.addEventListener('click', async () => {
      await applyDiscoveredDecision('reject');
      await fetchOverview();
    });
  }
  if (
    typeof discoveredLaterBtn !== 'undefined' &&
    discoveredLaterBtn instanceof HTMLButtonElement
  ) {
    discoveredLaterBtn.addEventListener('click', async () => {
      await applyDiscoveredDecision('snooze');
      await fetchOverview();
    });
  }

  if (
    typeof settingsTabButtons !== 'undefined' &&
    typeof settingsTabButtons.forEach === 'function'
  ) {
    settingsTabButtons.forEach((button) => {
      if (!(button instanceof HTMLButtonElement)) {
        return;
      }
      button.addEventListener('click', () => {
        const nextTab = button.dataset.settingsTab || 'auth';
        setSettingsTab(nextTab);
      });
    });
  }
  if (typeof settingsSaveBtn !== 'undefined' && settingsSaveBtn instanceof HTMLButtonElement) {
    settingsSaveBtn.addEventListener('click', saveSettings);
  }
  if (typeof settingsResetBtn !== 'undefined' && settingsResetBtn instanceof HTMLButtonElement) {
    settingsResetBtn.addEventListener('click', resetSettings);
  }
  if (
    typeof refreshSettingsBtn !== 'undefined' &&
    refreshSettingsBtn instanceof HTMLButtonElement
  ) {
    refreshSettingsBtn.addEventListener('click', fetchSettingsData);
  }

  if (
    typeof toggleWebcamFormPanelBtn !== 'undefined' &&
    typeof webcamFormContent !== 'undefined' &&
    toggleWebcamFormPanelBtn instanceof HTMLButtonElement &&
    webcamFormContent instanceof HTMLElement
  ) {
    setNodeFormPanelCollapsed(getStoredNodeFormCollapsedPreference());
    toggleWebcamFormPanelBtn.addEventListener('click', toggleNodeFormPanel);
  }
  tableBody.addEventListener('click', onTableClick);
  document.getElementById('webcam-transport').addEventListener('change', (event) => {
    const target = event.target;
    if (!(target instanceof HTMLSelectElement)) {
      return;
    }

    updateBaseUrlValidation(target.value);
  });
  updateBaseUrlValidation(document.getElementById('webcam-transport').value);
  if (
    diagnosticsAdvancedCheckbox instanceof HTMLInputElement &&
    diagnosticsCollapsibleContainer instanceof HTMLElement
  ) {
    setDiagnosticPanelExpanded(false);
    diagnosticsAdvancedCheckbox.addEventListener('change', toggleDiagnosticPanelContent);
  }
  if (
    typeof copyDiagnosticReportBtn !== 'undefined' &&
    copyDiagnosticReportBtn &&
    typeof copyDiagnosticReportBtn.addEventListener === 'function'
  ) {
    copyDiagnosticReportBtn.addEventListener('click', async () => {
      if (!latestDiagnosticResult) {
        showFeedback('Run Diagnose first to generate a report.', true);
        return;
      }

      const report = buildDiagnosticTextReport(latestDiagnosticResult);

      if (typeof globalThis.navigator?.clipboard?.writeText !== 'function') {
        showFeedback('Clipboard not available in this browser.', true);
        return;
      }

      try {
        await globalThis.navigator.clipboard.writeText(report);
        showFeedback('Diagnostic report copied to clipboard.');
      } catch {
        showFeedback('Could not copy report to clipboard.', true);
      }
    });
  }

  if (typeof setSettingsTab === 'function') {
    setSettingsTab('auth');
  }
  if (typeof setActiveView === 'function' && typeof getViewFromLocationHash === 'function') {
    setActiveView(getViewFromLocationHash());
  }
  if (typeof fetchWebcams === 'function') {
    await fetchWebcams();
  }
  if (typeof refreshStatuses === 'function') {
    await refreshStatuses();
  }
  if (typeof fetchOverview === 'function') {
    await fetchOverview();
  }
  if (typeof fetchSettingsData === 'function') {
    await fetchSettingsData();
  }
  if (typeof renderDiscoveredPanel === 'function') {
    renderDiscoveredPanel();
  }
  if (typeof renderOverviewPanel === 'function') {
    renderOverviewPanel();
  }
  if (typeof startStatusRefreshInterval === 'function') {
    startStatusRefreshInterval();
  }
}

init().catch((error) => {
  showFeedback(error.message || 'Failed to load management data.', true);
});
