// @ts-nocheck
import { bindNavigation, initializeManagementDashboard } from "./management-bootstrap.js";
import { setActiveView as setManagementActiveView } from "./management-navigation.js";
import { renderDiscoveredPanel as renderDiscoveredPanelContent, renderOverviewPanel as renderOverviewPanelContent, } from "./management-renderers.js";
import { createStatusRefresher } from "./management-status.js";
import { describeManagementApiError as describeApiError, fetchManagementSettings, saveManagementSettings, } from "./management-settings-api.js";
import { buildManagementSettingsPatch, hydrateManagementSettingsForm, } from "./management-settings-view.js";
import { renderDiagnosticResults as renderDiagnosticResultsUi } from "./management-diagnostic-renderer.js";
import { getDiagnosticCheckRows, getDiagnosticSummaryState, } from "./management-diagnostics.js";
import { isFailureStatus, normalizeWebcamStatusError, STATUS_SUBTYPE_CONFIG, statusClass, } from "./management-domain.js";
/**
 * Motion In Ocean Management Dashboard
 *
 * BUI for managing remote camera nodes, including registration, discovery, status monitoring,
 * diagnostics, and remote action execution. Implements webcam CRUD operations, bearer token
 * authentication, and real-time status polling.
 */
const tableBody = document.getElementById("webcams-table-body");
const webcamForm = document.getElementById("webcam-form");
const feedback = document.getElementById("form-feedback");
const formTitle = document.getElementById("form-title");
const cancelEditBtn = document.getElementById("cancel-edit-btn");
const refreshBtn = document.getElementById("refresh-webcams-btn");
const toggleWebcamFormPanelBtn = document.getElementById("toggle-webcam-form-panel-btn");
const managementLayout = document.getElementById("management-layout");
const webcamFormPanelContainer = document.getElementById("webcam-form-panel-container");
const webcamFormContentWrapper = document.getElementById("webcam-form-content-wrapper");
const webcamFormContent = document.getElementById("webcam-form-content");
const editingWebcamIdInput = document.getElementById("editing-webcam-id");
const diagnosticWebcamId = document.getElementById("diagnostic-webcam-id");
const diagnosticContext = document.getElementById("diagnostic-context");
const diagnosticSummaryBadge = document.getElementById("diagnostic-summary-badge");
const diagnosticOverallStatePill = document.getElementById("diagnostic-overall-state-pill");
const diagnosticSummaryInterpretation = document.getElementById("diagnostic-summary-interpretation");
const diagnosticSummaryCta = document.getElementById("diagnostic-summary-cta");
const diagnosticChecksGrid = document.getElementById("diagnostic-checks-grid");
const diagnosticRecommendations = document.getElementById("diagnostic-recommendations");
const copyDiagnosticReportBtn = document.getElementById("copy-diagnostic-report-btn");
const diagnosticPanel = document.getElementById("diagnostic-panel");
const advancedDiagnosticsToggle = document.getElementById("advanced-diagnostics-toggle");
const diagnosticPanelContent = document.getElementById("diagnostic-panel-content");
const diagnosticsAdvancedCheckbox = advancedDiagnosticsToggle;
const diagnosticsCollapsibleContainer = diagnosticPanelContent;
const managementMain = document.getElementById("management-main");
const overviewView = document.getElementById("overview-view");
const devicesView = document.getElementById("devices-view");
const discoveredView = document.getElementById("discovered-view");
const settingsView = document.getElementById("settings-view");
const overviewTotalWebcams = document.getElementById("overview-total-webcams");
const overviewHealthyWebcams = document.getElementById("overview-healthy-webcams");
const overviewUnavailableWebcams = document.getElementById("overview-unavailable-webcams");
const overviewStreamingWebcams = document.getElementById("overview-streaming-webcams");
const overviewActivityList = document.getElementById("overview-activity-list");
const overviewActionList = document.getElementById("overview-action-list");
const refreshDashboardBtn = document.getElementById("refresh-dashboard-btn");
const scanDiscoveredBtn = document.getElementById("scan-discovered-btn");
const discoveredList = document.getElementById("discovered-list");
const discoveredNotes = document.getElementById("discovered-notes");
const discoveredFeedback = document.getElementById("discovered-feedback");
const discoveredApproveBtn = document.getElementById("discovered-approve-btn");
const discoveredRejectBtn = document.getElementById("discovered-reject-btn");
const discoveredLaterBtn = document.getElementById("discovered-later-btn");
const viewOverviewBtn = document.getElementById("view-overview-btn");
const viewDevicesBtn = document.getElementById("view-devices-btn");
const viewDiscoveredBtn = document.getElementById("view-discovered-btn");
const viewSettingsBtn = document.getElementById("view-settings-btn");
const railOverviewBtn = document.getElementById("rail-overview-btn");
const railDevicesBtn = document.getElementById("rail-devices-btn");
const railDiscoveredBtn = document.getElementById("rail-discovered-btn");
const railSettingsBtn = document.getElementById("rail-settings-btn");
const railExportBtn = document.getElementById("rail-export-btn");
const railHelpBtn = document.getElementById("rail-help-btn");
const mobileOverviewBtn = document.getElementById("mobile-overview-btn");
const mobileDevicesBtn = document.getElementById("mobile-devices-btn");
const mobileDiscoveredBtn = document.getElementById("mobile-discovered-btn");
const mobileSettingsBtn = document.getElementById("mobile-settings-btn");
const mobileExportBtn = document.getElementById("mobile-export-btn");
const mobileHelpBtn = document.getElementById("mobile-help-btn");
const themeToggleBtn = document.getElementById("theme-toggle-btn");
const refreshSettingsBtn = document.getElementById("refresh-settings-btn");
const settingsSaveBtn = document.getElementById("settings-save-btn");
const settingsResetBtn = document.getElementById("settings-reset-btn");
const settingsFeedback = document.getElementById("settings-feedback");
const settingsManagementApiToken = document.getElementById("settings-management-api-token");
const settingsDiscoveryEnabled = document.getElementById("settings-discovery-enabled");
const settingsDiscoveryUrl = document.getElementById("settings-discovery-url");
const settingsDiscoveryToken = document.getElementById("settings-discovery-token");
const settingsDiscoveryInterval = document.getElementById("settings-discovery-interval");
const settingsRuntimeSummary = document.getElementById("settings-runtime-summary");
const settingsValidationSummary = document.getElementById("settings-validation-summary");
const settingsOverridesList = document.getElementById("settings-overrides-list");
const settingsTabButtons = document.querySelectorAll("[data-settings-tab]");
const settingsAuthPanel = document.getElementById("settings-auth-panel");
const settingsDiscoveryPanel = document.getElementById("settings-discovery-panel");
const settingsRuntimePanel = document.getElementById("settings-runtime-panel");
const utilityPanel = document.getElementById("utility-panel");
const utilityPanelTitle = document.getElementById("utility-panel-title");
const utilityPanelContent = document.getElementById("utility-panel-content");
const utilityPanelCloseBtn = document.getElementById("utility-panel-close-btn");
const managementApiTokenInput = document.getElementById("management-api-token");
let webcams = [];
let webcamStatusMap = new Map();
let webcamStatusAggregationMap = new Map();
let webcamDatasetVersion = 0;
let statusRefreshIntervalId;
let latestDiagnosticResult = null;
let overviewSnapshot = null;
let selectedDiscoveredNodeId = "";
let activityFeed = [];
let previousStatusByNode = new Map();
let discoveredSnoozedIds = new Set();
let managementApiBearerToken = "";
const API_AUTH_HINT = "Management API request unauthorized. Provide a valid Management API Bearer Token, then click Refresh to retry.";
const DOCKER_BASE_URL_PATTERN = String.raw `docker://[^\s/:]+:\d+/[^\s/]+`;
const DOCKER_BASE_URL_HINT = "Use format: docker://proxy-hostname:port/container-id";
const NODE_FORM_COLLAPSED_STORAGE_KEY = "management.webcamFormCollapsed";
const VIEW_HASH_PREFIX = "#";
const VIEWS = ["overview", "devices", "discovered", "settings"];
const THEME_STORAGE_KEY = "management.theme";
const API_TOKEN_STORAGE_KEY = "management.apiToken";
const SNOOZE_STORAGE_KEY = "management.discoveredSnoozedIds";
function setDiagnosticPanelExpanded(isExpanded) {
    if (!(diagnosticsAdvancedCheckbox instanceof HTMLInputElement) ||
        !(diagnosticsCollapsibleContainer instanceof HTMLElement)) {
        return;
    }
    diagnosticsAdvancedCheckbox.checked = isExpanded;
    diagnosticsCollapsibleContainer.hidden = !isExpanded;
    diagnosticsCollapsibleContainer.classList.toggle("hidden", !isExpanded);
    if (diagnosticPanel instanceof HTMLElement) {
        diagnosticPanel.classList.toggle("diagnostic-panel--collapsed", !isExpanded);
    }
}
function getMissingRequiredElementIds() {
    const requiredElements = [
        ["webcams-table-body", tableBody],
        ["webcam-form", webcamForm],
        ["form-title", formTitle],
        ["cancel-edit-btn", cancelEditBtn],
        ["refresh-webcams-btn", refreshBtn],
        ["editing-webcam-id", editingWebcamIdInput],
        ["webcam-transport", document.getElementById("webcam-transport")],
        ["copy-diagnostic-report-btn", copyDiagnosticReportBtn],
        ["management-main", managementMain],
        ["overview-view", overviewView],
        ["devices-view", devicesView],
        ["discovered-view", discoveredView],
        ["settings-view", settingsView],
        ["view-overview-btn", viewOverviewBtn],
        ["view-devices-btn", viewDevicesBtn],
        ["view-discovered-btn", viewDiscoveredBtn],
        ["view-settings-btn", viewSettingsBtn],
        ["theme-toggle-btn", themeToggleBtn],
    ];
    return requiredElements.filter(([, element]) => element == null).map(([id]) => id);
}
function isDiagnosticPanelContentVisible() {
    if (!(diagnosticsCollapsibleContainer instanceof HTMLElement)) {
        return false;
    }
    return (!diagnosticsCollapsibleContainer.hidden &&
        !diagnosticsCollapsibleContainer.classList.contains("hidden"));
}
function toggleDiagnosticPanelContent() {
    if (!(diagnosticsAdvancedCheckbox instanceof HTMLInputElement)) {
        return;
    }
    setDiagnosticPanelExpanded(diagnosticsAdvancedCheckbox.checked);
}
function updateBaseUrlValidation(transport = "http") {
    const baseUrlInput = document.getElementById("webcam-base-url");
    if (!(baseUrlInput instanceof HTMLInputElement)) {
        return;
    }
    baseUrlInput.setCustomValidity("");
    if (transport === "docker") {
        baseUrlInput.removeAttribute("type");
        baseUrlInput.setAttribute("pattern", DOCKER_BASE_URL_PATTERN);
        baseUrlInput.title = DOCKER_BASE_URL_HINT;
        return;
    }
    baseUrlInput.type = "url";
    baseUrlInput.setAttribute("pattern", String.raw `https?://[^\s]+`);
    baseUrlInput.title = "Must be a valid HTTP or HTTPS URL";
}
function formatDateTime(isoString) {
    if (!isoString) {
        return "—";
    }
    const parsed = new Date(isoString);
    if (Number.isNaN(parsed.getTime())) {
        return isoString;
    }
    return parsed.toLocaleString();
}
function getDiscoveryInfo(webcam = {}) {
    const discovery = webcam.discovery || {};
    const source = discovery.source || "manual";
    const firstSeen = discovery.first_seen || webcam.last_seen || null;
    const lastAnnounceAt = discovery.last_announce_at || null;
    const approved = source === "discovered" ? discovery.approved === true : true;
    return { source, firstSeen, lastAnnounceAt, approved };
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
    feedback.style.color = isError ? "#b91c1c" : "#166534";
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
    const normalized = String(token || "").trim();
    managementApiBearerToken = normalized;
    syncManagementTokenInputs(normalized);
    if (!persist) {
        return;
    }
    try {
        if (normalized) {
            globalThis.localStorage?.setItem(API_TOKEN_STORAGE_KEY, normalized);
        }
        else {
            globalThis.localStorage?.removeItem(API_TOKEN_STORAGE_KEY);
        }
    }
    catch {
        // Ignore local storage failures.
    }
}
function initializeManagementBearerToken() {
    let storedToken = "";
    try {
        storedToken = globalThis.localStorage?.getItem(API_TOKEN_STORAGE_KEY) || "";
    }
    catch {
        // Ignore local storage failures.
    }
    const fallbackInputToken = managementApiTokenInput instanceof HTMLInputElement ? managementApiTokenInput.value.trim() : "";
    setManagementBearerToken(storedToken || fallbackInputToken, { persist: false });
}
function openUtilityPanel(title, htmlContent) {
    if (!(utilityPanel instanceof HTMLElement) ||
        !(utilityPanelTitle instanceof HTMLElement) ||
        !(utilityPanelContent instanceof HTMLElement)) {
        return;
    }
    utilityPanelTitle.textContent = title;
    utilityPanelContent.innerHTML = htmlContent;
    utilityPanel.classList.remove("hidden");
}
function closeUtilityPanel() {
    if (!(utilityPanel instanceof HTMLElement)) {
        return;
    }
    utilityPanel.classList.add("hidden");
}
function openHelpPanel() {
    openUtilityPanel("Connection Help", `
      <ul class="overview-list">
        <li>Browser → Management: use the dashboard token (MANAGEMENT_AUTH_TOKEN) for management API requests.</li>
        <li>Management → Webcam: configure each node's webcam bearer token to match that webcam's WEBCAM_CONTROL_PLANE_AUTH_TOKEN.</li>
        <li>Use Diagnose on a node to inspect DNS, network, and API endpoint health.</li>
        <li>Discovery approvals activate announced nodes; reject keeps them pending.</li>
        <li>Private-IP and SSRF protections can block unsafe targets by policy.</li>
      </ul>
    `);
}
function openExportPanel() {
    if (!latestDiagnosticResult) {
        openUtilityPanel("Export Diagnostic Report", "<p>No diagnostic report is available yet. Run <strong>Diagnose</strong> for any node first.</p>");
        return;
    }
    const report = buildDiagnosticTextReport(latestDiagnosticResult);
    openUtilityPanel("Export Diagnostic Report", `
      <p>Most recent diagnostic report is available below.</p>
      <pre class="utility-panel__report">${escapeHtml(report)}</pre>
    `);
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
    const type = document.getElementById("webcam-auth-type").value;
    if (type !== "bearer") {
        return { type: "none" };
    }
    const token = document.getElementById("webcam-auth-token").value.trim();
    return token ? { type, token } : { type };
}
function getParsedLabels() {
    const raw = document.getElementById("webcam-labels").value.trim();
    if (!raw) {
        return {};
    }
    return JSON.parse(raw);
}
function buildWebcamPayload({ preserveLastSeen = false } = {}) {
    const nowIso = new Date().toISOString();
    const capabilities = document
        .getElementById("webcam-capabilities")
        .value.split(",")
        .map((entry) => entry.trim())
        .filter(Boolean);
    const payload = {
        id: document.getElementById("webcam-id").value.trim(),
        name: document.getElementById("webcam-name").value.trim(),
        base_url: document.getElementById("webcam-base-url").value.trim(),
        transport: document.getElementById("webcam-transport").value,
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
    }
    else {
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
    return fragments.join(" • ");
}
function getStatusReason(status = {}) {
    const code = status.error_code;
    const knownReasons = {
        SSRF_BLOCKED: {
            title: "Private-IP policy blocked this webcam target.",
            hint: "Use a docker network hostname (e.g., 'motion-in-ocean-webcam:8000') or explicitly set MIO_ALLOW_PRIVATE_IPS=true on management for trusted internal networks. Click Diagnose for details.",
        },
        NETWORK_UNREACHABLE: {
            title: "Node is unreachable on the network.",
            hint: "Check webcam is running, network connectivity, and firewall rules. Click Diagnose for details.",
        },
        DOCKER_PROXY_UNREACHABLE: {
            title: "Docker proxy is unreachable.",
            hint: "Verify docker-socket-proxy is running and accessible on configured host and port. Click Diagnose for details.",
        },
        DOCKER_CONTAINER_NOT_FOUND: {
            title: "Container not found on docker proxy.",
            hint: "Verify the container ID/name is correct and running on the docker host.",
        },
        DOCKER_API_ERROR: {
            title: "Docker API returned an error.",
            hint: "Check docker proxy configuration and container status.",
        },
        INVALID_DOCKER_URL: {
            title: "Docker URL is invalid.",
            hint: "Use format: docker://proxy-hostname:port/container-id",
        },
        WEBCAM_UNREACHABLE: {
            title: "Node is unreachable.",
            hint: "Check the webcam base URL, networking, and that the webcam service is running.",
        },
        WEBCAM_UNAUTHORIZED: {
            title: "Token/auth mismatch with remote node.",
            hint: "Set this webcam bearer token to match WEBCAM_CONTROL_PLANE_AUTH_TOKEN on the remote webcam, then refresh.",
        },
        WEBCAM_INVALID_RESPONSE: {
            title: "Node returned an invalid response.",
            hint: "Verify the webcam API version and status endpoint compatibility.",
        },
        TRANSPORT_UNSUPPORTED: {
            title: "Configured transport is unsupported.",
            hint: "Switch to a supported transport for this node.",
        },
        WEBCAM_API_MISMATCH: {
            title: "Node API does not match expected management endpoints.",
            hint: "Confirm the webcam is running the compatible management service and exposes /api/status.",
        },
    };
    if (code && knownReasons[code]) {
        const reason = knownReasons[code];
        return `${reason.title} ${reason.hint}`;
    }
    if (status.error_message) {
        return status.error_message;
    }
    return "No additional details available.";
}
function normalizeWebcamStatusForUi(status = {}) {
    const statusText = String(status.status || "unknown").toLowerCase();
    const errorCode = String(status.error_code || "").toUpperCase();
    const isReady = status.ready === true;
    const subtype = getWebcamStatusSubtype(statusText, errorCode, isReady);
    const config = STATUS_SUBTYPE_CONFIG[subtype] || {
        label: "Unknown",
        helpText: "Node state is unknown.",
        statusClass: statusClass(statusText),
    };
    let reasonText = getStatusReason(status);
    if (subtype === "healthy") {
        reasonText = "Ready and responding.";
    }
    else if (subtype === "partial_probe") {
        reasonText = status.error_message || "Node responded, but readiness is incomplete.";
    }
    else if (subtype === "degraded") {
        reasonText = status.error_message || "Node is reachable, but operating in a degraded mode.";
    }
    return {
        subtype,
        label: config.label,
        helpText: config.helpText,
        statusClass: config.statusClass,
        reasonText,
    };
}
function getWebcamStatusSubtype(statusText, errorCode, isReady) {
    if (errorCode === "TRANSPORT_UNSUPPORTED")
        return "unsupported_transport";
    if (errorCode === "WEBCAM_UNAUTHORIZED" || statusText === "unauthorized") {
        return "unauthorized";
    }
    if (["ok", "healthy", "ready"].includes(statusText)) {
        return isReady ? "healthy" : "partial_probe";
    }
    if (["degraded", "warning"].includes(statusText))
        return "degraded";
    if (["partial", "probing"].includes(statusText))
        return "partial_probe";
    return "no_response";
}
function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value == null ? "" : String(value);
    return div.innerHTML;
}
function setTextContent(element, text) {
    if (element instanceof HTMLElement) {
        element.textContent = text;
    }
}
function getViewFromLocationHash() {
    const rawHash = String(globalThis.location?.hash || "").replace(VIEW_HASH_PREFIX, "");
    return VIEWS.includes(rawHash) ? rawHash : "overview";
}
function setActiveView(view) {
    setManagementActiveView(view, VIEWS, {
        views: {
            overview: overviewView,
            devices: devicesView,
            discovered: discoveredView,
            settings: settingsView,
        },
        buttons: {
            overview: viewOverviewBtn,
            devices: viewDevicesBtn,
            discovered: viewDiscoveredBtn,
            settings: viewSettingsBtn,
        },
        railButtons: {
            overview: [railOverviewBtn, mobileOverviewBtn],
            devices: [railDevicesBtn, mobileDevicesBtn],
            discovered: [railDiscoveredBtn, mobileDiscoveredBtn],
            settings: [railSettingsBtn, mobileSettingsBtn],
        },
        location: globalThis.location,
        history: globalThis.history,
    });
}
function applyTheme(theme) {
    const resolvedTheme = theme === "dark" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", resolvedTheme);
    setTextContent(themeToggleBtn, resolvedTheme === "dark" ? "Light Theme" : "Dark Theme");
    try {
        globalThis.localStorage?.setItem(THEME_STORAGE_KEY, resolvedTheme);
    }
    catch {
        // Ignore local storage failures.
    }
}
function initializeTheme() {
    let preferredTheme = "light";
    try {
        preferredTheme = globalThis.localStorage?.getItem(THEME_STORAGE_KEY) || "light";
    }
    catch {
        // Ignore local storage failures.
    }
    applyTheme(preferredTheme);
}
function getDiscoveredNodes() {
    return webcams.filter((node) => {
        const discovery = getDiscoveryInfo(node);
        return discovery.source === "discovered" && !discovery.approved;
    });
}
function loadSnoozedDiscoveredIds() {
    try {
        const raw = globalThis.localStorage?.getItem(SNOOZE_STORAGE_KEY) || "[]";
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) {
            discoveredSnoozedIds = new Set(parsed.filter((entry) => typeof entry === "string"));
        }
    }
    catch {
        discoveredSnoozedIds = new Set();
    }
}
function persistSnoozedDiscoveredIds() {
    try {
        globalThis.localStorage?.setItem(SNOOZE_STORAGE_KEY, JSON.stringify(Array.from(discoveredSnoozedIds)));
    }
    catch {
        // Ignore local storage failures.
    }
}
function appendActivityFeed(message, level = "info") {
    const timestamp = new Date().toISOString();
    activityFeed.unshift({ timestamp, message, level });
    if (activityFeed.length > 40) {
        activityFeed = activityFeed.slice(0, 40);
    }
}
function renderOverviewPanel() {
    renderOverviewPanelContent({
        snapshot: overviewSnapshot,
        activityFeed,
        statuses: webcamStatusMap,
        pendingDiscoveryCount: getDiscoveredNodes().length,
        totalElement: overviewTotalWebcams,
        healthyElement: overviewHealthyWebcams,
        unavailableElement: overviewUnavailableWebcams,
        streamingElement: overviewStreamingWebcams,
        activityElement: overviewActivityList,
        actionElement: overviewActionList,
        escapeHtml,
    });
}
function renderDiscoveredPanel() {
    selectedDiscoveredNodeId = renderDiscoveredPanelContent({
        nodes: getDiscoveredNodes(),
        snoozedIds: discoveredSnoozedIds,
        selectedNodeId: selectedDiscoveredNodeId,
        statuses: webcamStatusMap,
        listElement: discoveredList,
        notesElement: discoveredNotes,
        actionButtons: [discoveredApproveBtn, discoveredRejectBtn, discoveredLaterBtn],
        escapeHtml,
    });
}
async function fetchOverview() {
    try {
        const response = await managementFetch("/api/v1/management/overview");
        if (!response.ok) {
            return;
        }
        const payload = await response.json();
        overviewSnapshot = payload.summary || null;
        renderOverviewPanel();
    }
    catch {
        // Non-fatal: overview panel can still render from current status maps.
    }
}
function setDiscoveredFeedback(message, isError = false) {
    if (!(discoveredFeedback instanceof HTMLElement)) {
        return;
    }
    discoveredFeedback.textContent = message;
    discoveredFeedback.style.color = isError ? "#b91c1c" : "#166534";
}
async function applyDiscoveredDecision(decision) {
    if (!selectedDiscoveredNodeId) {
        setDiscoveredFeedback("Select a discovered node first.", true);
        return;
    }
    if (decision === "snooze") {
        discoveredSnoozedIds.add(selectedDiscoveredNodeId);
        persistSnoozedDiscoveredIds();
        setDiscoveredFeedback(`Node ${selectedDiscoveredNodeId} snoozed for this browser session.`);
        renderDiscoveredPanel();
        return;
    }
    const success = await setDiscoveryApproval(selectedDiscoveredNodeId, decision);
    if (success) {
        setDiscoveredFeedback(`Node ${selectedDiscoveredNodeId} ${decision}d.`);
    }
    else {
        setDiscoveredFeedback(`Could not ${decision} node ${selectedDiscoveredNodeId}.`, true);
    }
}
function setSettingsFeedback(message, isError = false) {
    if (!(settingsFeedback instanceof HTMLElement)) {
        return;
    }
    settingsFeedback.textContent = message;
    settingsFeedback.style.color = isError ? "#b91c1c" : "#166534";
}
function setSettingsTab(tabName) {
    const panels = {
        auth: settingsAuthPanel,
        discovery: settingsDiscoveryPanel,
        runtime: settingsRuntimePanel,
    };
    for (const [name, panel] of Object.entries(panels)) {
        if (panel instanceof HTMLElement) {
            panel.classList.toggle("hidden", name !== tabName);
        }
    }
    settingsTabButtons.forEach((button) => {
        if (!(button instanceof HTMLButtonElement)) {
            return;
        }
        const active = button.dataset.settingsTab === tabName;
        button.classList.toggle("management-view-btn--active", active);
        button.setAttribute("aria-current", active ? "true" : "false");
    });
}
function renderRuntimeSettingsChanges(changesPayload = {}) {
    const overridden = Array.isArray(changesPayload.overridden) ? changesPayload.overridden : [];
    if (settingsRuntimeSummary instanceof HTMLElement) {
        settingsRuntimeSummary.textContent =
            overridden.length > 0 ? "Using custom values" : "Using environment defaults";
    }
    if (settingsOverridesList instanceof HTMLElement) {
        settingsOverridesList.innerHTML = overridden.length
            ? overridden
                .map((entry) => `<li>${escapeHtml(entry.category || "unknown")}.${escapeHtml(entry.key || "unknown")} = ${escapeHtml(JSON.stringify(entry.value))}</li>`)
                .join("")
            : "<li>No overrides.</li>";
    }
}
async function fetchSettingsData() {
    try {
        const { settings, changes } = await fetchManagementSettings(managementFetch);
        hydrateManagementSettingsForm(settings.discovery, {
            enabled: settingsDiscoveryEnabled,
            url: settingsDiscoveryUrl,
            token: settingsDiscoveryToken,
            interval: settingsDiscoveryInterval,
        });
        if (changes !== undefined) {
            renderRuntimeSettingsChanges(changes);
        }
        if (settingsValidationSummary instanceof HTMLElement) {
            settingsValidationSummary.textContent = "Validation summary";
        }
    }
    catch (error) {
        setSettingsFeedback(error instanceof Error ? error.message : "Failed to load settings.", true);
    }
}
async function saveSettings() {
    if (settingsManagementApiToken instanceof HTMLInputElement) {
        setManagementBearerToken(settingsManagementApiToken.value);
    }
    const patchPayload = buildManagementSettingsPatch({
        enabled: settingsDiscoveryEnabled,
        url: settingsDiscoveryUrl,
        token: settingsDiscoveryToken,
        interval: settingsDiscoveryInterval,
    });
    if (!patchPayload)
        return;
    setSettingsFeedback("");
    const result = await saveManagementSettings(managementFetch, patchPayload);
    if (result.kind === "restart-required") {
        setSettingsFeedback("Saved. Some changes require restart to take effect.");
        if (settingsValidationSummary instanceof HTMLElement) {
            settingsValidationSummary.textContent = `Requires restart (${result.modifiedOnRestart.length})`;
        }
        await fetchSettingsData();
        return;
    }
    if (result.kind === "failure") {
        setSettingsFeedback(result.message || "Failed to save settings.", true);
        return;
    }
    setSettingsFeedback("Settings saved.");
    if (settingsValidationSummary instanceof HTMLElement) {
        settingsValidationSummary.textContent = "Validation summary";
    }
    await fetchSettingsData();
}
async function resetSettings() {
    setSettingsFeedback("");
    try {
        const response = await managementFetch("/api/v1/settings/reset", { method: "POST" });
        if (!response.ok) {
            setSettingsFeedback("Reset failed.", true);
            return;
        }
        setSettingsFeedback("Settings reset to defaults.");
        await fetchSettingsData();
    }
    catch (error) {
        setSettingsFeedback(error?.message || "Reset failed.", true);
    }
}
function renderRows() {
    if (!webcams.length) {
        tableBody.innerHTML = '<tr><td colspan="8" class="empty">No nodes registered.</td></tr>';
        return;
    }
    tableBody.innerHTML = webcams
        .map((node) => {
        const status = webcamStatusMap.get(node.id) || { status: "unknown", stream_available: false };
        const normalizedStatus = normalizeWebcamStatusForUi(status);
        const streamText = status.stream_available ? "Available" : "Unavailable";
        const discovery = getDiscoveryInfo(node);
        const aggregateDetails = formatAggregationDetails(status);
        const detailsTooltip = [normalizedStatus.helpText, status.error_details]
            .filter(Boolean)
            .join(" ");
        const approvalHint = discovery.source === "discovered" && !discovery.approved
            ? "Pending approval before full activation."
            : "";
        const detailsText = [approvalHint, normalizedStatus.reasonText].filter(Boolean).join(" ");
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
              Approval: ${escapeHtml(discovery.approved ? "approved" : "pending")}
            </small>
          </td>
          <td>
            <span class="ui-status-pill ${normalizedStatus.statusClass}" title="${escapeHtml(normalizedStatus.helpText)}">${escapeHtml(normalizedStatus.label)}</span>
          </td>
          <td>
            <small title="${escapeHtml(detailsTooltip)}">${escapeHtml(detailsText)}</small>
            ${aggregateDetails ? `<br><small>${escapeHtml(aggregateDetails)}</small>` : ""}
          </td>
          <td>${streamText}</td>
          <td>
            <div class="row-actions">
              <button class="ui-btn ui-btn--secondary" data-action="edit" data-id="${escapeHtml(node.id)}">Edit</button>
              <button class="ui-btn ui-btn--secondary" data-action="diagnose" data-id="${escapeHtml(node.id)}">Diagnose</button>
              ${discovery.source === "discovered" ? `<button class="ui-btn ui-btn--secondary" data-action="approve" data-id="${escapeHtml(node.id)}">Approve</button><button class="ui-btn ui-btn--secondary" data-action="reject" data-id="${escapeHtml(node.id)}">Reject</button>` : ""}
              <button class="ui-btn ui-btn--danger" data-action="delete" data-id="${escapeHtml(node.id)}">Remove</button>
            </div>
          </td>
        </tr>
      `;
    })
        .join("");
}
/**
 * Fetch all registered nodes from API and update UI.
 *
 * @async
 * @returns {Promise<void>}
 */
async function fetchWebcams() {
    try {
        const response = await managementFetch("/api/v1/webcams");
        if (!response.ok) {
            throw new Error("Failed to load nodes");
        }
        const payload = await response.json();
        webcams = payload.webcams || payload.nodes || [];
        webcamDatasetVersion += 1;
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
    }
    catch (error) {
        if (error?.isUnauthorized) {
            showFeedback(API_AUTH_HINT, true);
        }
        else {
            showFeedback(error.message || "Failed to load nodes", true);
        }
        throw error;
    }
}
/** Refresh the node list, statuses, and overview using one consistent sequence. */
async function refreshManagementData() {
    await fetchWebcams();
    await refreshStatuses();
    await fetchOverview();
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
const refreshStatusCoordinator = createStatusRefresher({
    getNodes: () => webcams,
    getDatasetVersion: () => webcamDatasetVersion,
    getStatusHistory: () => previousStatusByNode,
    fetchStatusesForNodes,
    setStatuses: (statuses) => {
        webcamStatusMap = statuses;
    },
    showUnauthorizedFeedback: () => showFeedback(API_AUTH_HINT, true),
    renderRows,
    renderDiscoveredPanel,
    renderOverviewPanel,
    appendActivityFeed,
});
function refreshStatuses(options = {}) {
    return refreshStatusCoordinator(options);
}
/** Fetch and normalize status for every node in a polling cycle. */
async function fetchStatusesForNodes(nodeIds, allowManualFeedback, onUnauthorized) {
    const statuses = new Map();
    await Promise.all(Array.from(nodeIds).map(async (nodeId) => {
        try {
            const response = await managementFetch(`/api/v1/webcams/${encodeURIComponent(nodeId)}/status`);
            if (!response.ok) {
                const parsed = await response.json().catch(() => ({}));
                const errorPayload = parsed?.error || parsed || {};
                statuses.set(nodeId, enrichStatusWithAggregation(nodeId, normalizeWebcamStatusError(errorPayload)));
                return;
            }
            statuses.set(nodeId, enrichStatusWithAggregation(nodeId, await response.json()));
        }
        catch (error) {
            if (allowManualFeedback && error?.isUnauthorized) {
                onUnauthorized();
            }
            statuses.set(nodeId, enrichStatusWithAggregation(nodeId, normalizeWebcamStatusError({
                message: error?.message || "Failed to refresh webcam status.",
            })));
        }
    }));
    return statuses;
}
function resetForm() {
    webcamForm.reset();
    updateBaseUrlValidation(document.getElementById("webcam-transport").value);
    editingWebcamIdInput.value = "";
    formTitle.textContent = "Add node";
    document.getElementById("webcam-id").disabled = false;
    cancelEditBtn.classList.add("hidden");
}
function setNodeFormPanelCollapsed(isCollapsed) {
    const isExpanded = !isCollapsed;
    if (!(toggleWebcamFormPanelBtn instanceof HTMLButtonElement) ||
        !(webcamFormContent instanceof HTMLElement)) {
        return;
    }
    if (managementLayout instanceof HTMLElement) {
        managementLayout.classList.toggle("is-form-collapsed", isCollapsed);
    }
    if (webcamFormPanelContainer instanceof HTMLElement) {
        webcamFormPanelContainer.classList.toggle("is-form-collapsed", isCollapsed);
    }
    if (webcamFormContentWrapper instanceof HTMLElement) {
        webcamFormContentWrapper.classList.toggle("hidden", isCollapsed);
    }
    webcamFormContent.classList.toggle("hidden", isCollapsed);
    toggleWebcamFormPanelBtn.setAttribute("aria-expanded", String(isExpanded));
    toggleWebcamFormPanelBtn.textContent = isExpanded ? "«" : "»";
    toggleWebcamFormPanelBtn.title = isExpanded
        ? "Collapse webcam form panel"
        : "Expand webcam form panel";
    toggleWebcamFormPanelBtn.setAttribute("aria-label", isExpanded ? "Collapse webcam form panel" : "Expand webcam form panel");
    try {
        globalThis.localStorage?.setItem(NODE_FORM_COLLAPSED_STORAGE_KEY, String(isCollapsed));
    }
    catch {
        // Ignore storage failures in private/incognito environments.
    }
}
function toggleNodeFormPanel() {
    if (!(toggleWebcamFormPanelBtn instanceof HTMLButtonElement)) {
        return;
    }
    const isExpanded = toggleWebcamFormPanelBtn.getAttribute("aria-expanded") === "true";
    setNodeFormPanelCollapsed(isExpanded);
}
function getStoredNodeFormCollapsedPreference() {
    try {
        return globalThis.localStorage?.getItem(NODE_FORM_COLLAPSED_STORAGE_KEY) === "true";
    }
    catch {
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
    showFeedback("");
    const editingNodeId = editingWebcamIdInput.value;
    const isEdit = Boolean(editingNodeId);
    let payload;
    try {
        payload = buildWebcamPayload({ preserveLastSeen: isEdit });
    }
    catch {
        showFeedback("Labels must be valid JSON.", true);
        return;
    }
    const endpoint = isEdit
        ? `/api/v1/webcams/${encodeURIComponent(editingNodeId)}`
        : "/api/v1/webcams";
    const method = isEdit ? "PUT" : "POST";
    try {
        const response = await managementFetch(endpoint, {
            method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        if (!response.ok) {
            const errorPayload = await response.json().catch(() => ({}));
            showFeedback(describeApiError(errorPayload), true);
            return;
        }
        showFeedback(isEdit ? "Node updated." : "Node added.");
        resetForm();
        await refreshManagementData();
    }
    catch (error) {
        if (error?.isUnauthorized) {
            showFeedback(API_AUTH_HINT, true);
            return;
        }
        showFeedback(error.message || "Network error occurred.", true);
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
    document.getElementById("webcam-id").value = webcam.id;
    document.getElementById("webcam-id").disabled = true;
    document.getElementById("webcam-name").value = webcam.name || "";
    document.getElementById("webcam-base-url").value = webcam.base_url || "";
    document.getElementById("webcam-transport").value = webcam.transport || "http";
    updateBaseUrlValidation(document.getElementById("webcam-transport").value);
    document.getElementById("webcam-auth-type").value = webcam.auth?.type || "none";
    document.getElementById("webcam-auth-token").value = webcam.auth?.token || "";
    document.getElementById("webcam-capabilities").value = (webcam.capabilities || []).join(", ");
    document.getElementById("webcam-labels").value = JSON.stringify(webcam.labels || {}, null, 2);
    cancelEditBtn.classList.remove("hidden");
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
        const response = await managementFetch(`/api/v1/webcams/${encodeURIComponent(nodeId)}/diagnose`);
        if (!response.ok) {
            const errorPayload = await response.json().catch(() => ({}));
            showFeedback(errorPayload?.error?.message || "Diagnostic request failed", true);
            return;
        }
        const diagnosticResult = await response.json();
        showDiagnosticResults(diagnosticResult);
    }
    catch (error) {
        if (error?.isUnauthorized) {
            showFeedback(API_AUTH_HINT, true);
            return;
        }
        showFeedback(error.message || "Network error occurred.", true);
    }
}
function renderDiagnosticRecommendations(guidance = [], recommendations = []) {
    const structured = recommendations.length
        ? recommendations
        : guidance.map((item) => ({ message: item, status: "warn" }));
    const recommendationsList = structured.length
        ? structured
            .map((item) => {
            const state = ["pass", "warn", "fail"].includes(item.status) ? item.status : "warn";
            const icon = state === "pass" ? "[PASS]" : state === "warn" ? "[WARN]" : "[FAIL]";
            const codeSuffix = item.code ? ` <small>(Code: ${escapeHtml(item.code)})</small>` : "";
            return `<li><span class="diagnostic-pill diagnostic-pill--${state}">${icon}</span> ${escapeHtml(item.message || "")}${codeSuffix}</li>`;
        })
            .join("")
        : "<li>No recommendations provided.</li>";
    diagnosticRecommendations.innerHTML = `
    <h4>Recommendations</h4>
    <ul>${recommendationsList}</ul>
  `;
}
function buildDiagnosticTextReport(diagnosticResult) {
    const nodeId = diagnosticResult.node_id || "unknown";
    const diagnostics = diagnosticResult.diagnostics || {};
    const guidance = diagnosticResult.guidance || [];
    const recommendations = diagnosticResult.recommendations || [];
    const checkRows = getDiagnosticCheckRows(diagnostics);
    const summary = getDiagnosticSummaryState(checkRows);
    let output = `Diagnostic Report\nNode: ${nodeId}\nSummary: ${summary.label}\n\nChecks:\n`;
    checkRows.forEach((row) => {
        const icon = row.state === "pass" ? "[PASS]" : row.state === "warn" ? "[WARN]" : "[FAIL]";
        output += `${icon} ${row.key}: ${row.detail}${row.meta ? ` (${row.meta})` : ""}\n`;
    });
    output += "\nRecommendations:\n";
    const reportRecommendations = recommendations.length
        ? recommendations
        : guidance.map((item) => ({ message: item, status: "warn" }));
    if (reportRecommendations.length === 0) {
        output += "- No recommendations provided.\n";
    }
    else {
        reportRecommendations.forEach((item) => {
            const icon = item.status === "pass" ? "[PASS]" : item.status === "fail" ? "[FAIL]" : "[WARN]";
            output += `- ${icon} ${item.message}${item.code ? ` (Code: ${item.code})` : ""}\n`;
        });
    }
    return output;
}
function showDiagnosticResults(diagnosticResult) {
    latestDiagnosticResult = diagnosticResult;
    renderDiagnosticResultsUi(diagnosticResult, {
        diagnosticWebcamId,
        diagnosticContext,
        diagnosticSummaryBadge,
        diagnosticOverallStatePill,
        diagnosticSummaryInterpretation,
        diagnosticSummaryCta,
        diagnosticChecksGrid,
        diagnosticRecommendations,
        copyDiagnosticReportBtn,
        diagnosticPanel,
        escapeHtml,
        renderRecommendations: renderDiagnosticRecommendations,
        setPanelExpanded: setDiagnosticPanelExpanded,
        isPanelContentVisible: isDiagnosticPanelContentVisible,
    });
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
        const response = await managementFetch(`/api/v1/webcams/${encodeURIComponent(nodeId)}/discovery/${decision}`, {
            method: "POST",
        });
        if (!response.ok) {
            const errorPayload = await response.json().catch(() => ({}));
            showFeedback(describeApiError(errorPayload), true);
            return false;
        }
        discoveredSnoozedIds.delete(nodeId);
        persistSnoozedDiscoveredIds();
        showFeedback(`Node ${nodeId} ${decision}d.`);
        await refreshManagementData();
        return true;
    }
    catch (error) {
        if (error?.isUnauthorized) {
            showFeedback(API_AUTH_HINT, true);
            return false;
        }
        showFeedback(error.message || "Network error occurred.", true);
        return false;
    }
}
async function removeNode(nodeId) {
    if (!window.confirm(`Delete webcam ${nodeId}?`)) {
        return;
    }
    try {
        const response = await managementFetch(`/api/v1/webcams/${encodeURIComponent(nodeId)}`, {
            method: "DELETE",
        });
        if (!response.ok) {
            const errorPayload = await response.json().catch(() => ({}));
            showFeedback(errorPayload?.error?.message || "Delete failed", true);
            return;
        }
        showFeedback(`Node ${nodeId} removed.`);
        if (editingWebcamIdInput.value === nodeId) {
            resetForm();
        }
        await refreshManagementData();
    }
    catch (error) {
        if (error?.isUnauthorized) {
            showFeedback(API_AUTH_HINT, true);
            return;
        }
        showFeedback(error.message || "Network error occurred.", true);
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
    if (action === "edit") {
        beginEditNode(nodeId);
    }
    else if (action === "delete") {
        removeNode(nodeId);
    }
    else if (action === "diagnose") {
        diagnoseNode(nodeId);
    }
    else if (action === "approve") {
        setDiscoveryApproval(nodeId, "approve");
    }
    else if (action === "reject") {
        setDiscoveryApproval(nodeId, "reject");
    }
}
function initializeManagementState() {
    if (typeof initializeTheme === "function")
        initializeTheme();
    if (typeof initializeManagementBearerToken === "function")
        initializeManagementBearerToken();
    if (typeof loadSnoozedDiscoveredIds === "function")
        loadSnoozedDiscoveredIds();
    const tokenInputs = [];
    if (typeof managementApiTokenInput !== "undefined")
        tokenInputs.push(managementApiTokenInput);
    if (typeof settingsManagementApiToken !== "undefined")
        tokenInputs.push(settingsManagementApiToken);
    tokenInputs.forEach((input) => {
        if (input instanceof HTMLInputElement) {
            input.addEventListener("input", () => setManagementBearerToken(input.value));
        }
    });
}
async function init() {
    const missingElementIds = getMissingRequiredElementIds();
    if (missingElementIds.length > 0) {
        const details = `Missing required management UI element(s): ${missingElementIds.join(", ")}`;
        console.error(`[management-ui] ${details}`);
        showFeedback("Management UI failed to initialize due to missing page elements.", true);
        return;
    }
    await initializeManagementDashboard({
        elements: {
            webcamForm,
            cancelEditBtn,
            refreshBtn,
            refreshDashboardBtn,
            scanDiscoveredBtn,
            discoveredList,
            discoveredApproveBtn,
            discoveredRejectBtn,
            discoveredLaterBtn,
            settingsTabButtons,
            settingsSaveBtn,
            settingsResetBtn,
            refreshSettingsBtn,
            toggleWebcamFormPanelBtn,
            webcamFormContent,
            tableBody,
            webcamTransport: document.getElementById("webcam-transport"),
            diagnosticsAdvancedCheckbox,
            diagnosticsCollapsibleContainer,
            copyDiagnosticReportBtn,
            viewOverviewBtn,
            viewDevicesBtn,
            viewDiscoveredBtn,
            viewSettingsBtn,
            railOverviewBtn,
            railDevicesBtn,
            railDiscoveredBtn,
            railSettingsBtn,
            mobileOverviewBtn,
            mobileDevicesBtn,
            mobileDiscoveredBtn,
            mobileSettingsBtn,
            railHelpBtn,
            mobileHelpBtn,
            railExportBtn,
            mobileExportBtn,
            utilityPanelCloseBtn,
            themeToggleBtn,
        },
        actions: {
            initializeManagementState,
            bindManagementNavigation: () => bindNavigation({
                elements: {
                    viewOverviewBtn,
                    viewDevicesBtn,
                    viewDiscoveredBtn,
                    viewSettingsBtn,
                    railOverviewBtn,
                    railDevicesBtn,
                    railDiscoveredBtn,
                    railSettingsBtn,
                    mobileOverviewBtn,
                    mobileDevicesBtn,
                    mobileDiscoveredBtn,
                    mobileSettingsBtn,
                    railHelpBtn,
                    mobileHelpBtn,
                    railExportBtn,
                    mobileExportBtn,
                    utilityPanelCloseBtn,
                    themeToggleBtn,
                },
                actions: {
                    setActiveView,
                    getViewFromLocationHash,
                    openHelpPanel,
                    openExportPanel,
                    closeUtilityPanel,
                    toggleTheme: () => {
                        const currentTheme = document.documentElement.getAttribute("data-theme") || "light";
                        applyTheme(currentTheme === "dark" ? "light" : "dark");
                    },
                },
            }),
            submitNodeForm,
            resetForm,
            showFeedback,
            stopStatusRefreshInterval,
            refreshManagementData,
            startStatusRefreshInterval,
            renderOverviewPanel,
            renderDiscoveredPanel,
            setDiscoveredFeedback,
            selectDiscoveredNode: (nodeId) => {
                selectedDiscoveredNodeId = nodeId;
            },
            applyDiscoveredDecision,
            fetchOverview,
            setSettingsTab,
            saveSettings,
            resetSettings,
            fetchSettingsData,
            setNodeFormPanelCollapsed,
            getStoredNodeFormCollapsedPreference,
            toggleNodeFormPanel,
            onTableClick,
            updateBaseUrlValidation,
            setDiagnosticPanelExpanded,
            toggleDiagnosticPanelContent,
            getLatestDiagnosticResult: () => latestDiagnosticResult,
            buildDiagnosticTextReport,
            fetchWebcams,
            refreshStatuses,
        },
    });
}
init().catch((error) => {
    showFeedback(error.message || "Failed to load management data.", true);
});
