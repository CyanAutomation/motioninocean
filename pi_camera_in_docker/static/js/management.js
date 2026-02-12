const tableBody = document.getElementById("nodes-table-body");
const nodeForm = document.getElementById("node-form");
const feedback = document.getElementById("form-feedback");
const formTitle = document.getElementById("form-title");
const cancelEditBtn = document.getElementById("cancel-edit-btn");
const refreshBtn = document.getElementById("refresh-nodes-btn");
const editingNodeIdInput = document.getElementById("editing-node-id");

let nodes = [];
let nodeStatusMap = new Map();
let nodeStatusAggregationMap = new Map();
let statusRefreshInFlight = false;
let statusRefreshPending = false;
let statusRefreshPendingManual = false;
let statusRefreshToken = 0;
let statusRefreshIntervalId;
const API_AUTH_HINT =
  "Management API request unauthorized. Provide a valid Management API Bearer Token, then click Refresh to retry.";

function showFeedback(message, isError = false) {
  feedback.textContent = message;
  feedback.style.color = isError ? "#b91c1c" : "#166534";
}

function getManagementBearerToken() {
  const tokenInput = document.getElementById("management-api-token");
  if (!(tokenInput instanceof HTMLInputElement)) {
    return "";
  }

  return tokenInput.value.trim();
}



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
  const type = document.getElementById("node-auth-type").value;

  if (type !== "bearer") {
    return { type: "none" };
  }

  const token = document.getElementById("node-auth-token").value.trim();
  return token ? { type, token } : { type };
}

function getParsedLabels() {
  const raw = document.getElementById("node-labels").value.trim();
  if (!raw) {
    return {};
  }
  return JSON.parse(raw);
}

function buildNodePayload({ preserveLastSeen = false } = {}) {
  const nowIso = new Date().toISOString();
  const capabilities = document
    .getElementById("node-capabilities")
    .value.split(",")
    .map((entry) => entry.trim())
    .filter(Boolean);

  const payload = {
    id: document.getElementById("node-id").value.trim(),
    name: document.getElementById("node-name").value.trim(),
    base_url: document.getElementById("node-base-url").value.trim(),
    transport: document.getElementById("node-transport").value,
    auth: getAuthPayload(),
    capabilities,
    labels: getParsedLabels(),
    last_seen: nowIso,
  };

  if (preserveLastSeen) {
    const existing = nodes.find((node) => node.id === editingNodeIdInput.value);
    if (existing?.last_seen) {
      payload.last_seen = existing.last_seen;
    }
  }

  return payload;
}

function statusClass(statusText) {
  const normalized = (statusText || "unknown").toLowerCase();
  if (["ok", "healthy", "ready"].includes(normalized)) {
    return "ui-status-pill--success";
  }
  if (["error", "down", "failed", "unhealthy"].includes(normalized)) {
    return "ui-status-pill--error";
  }
  return "ui-status-pill--neutral";
}

const STATUS_SUBTYPE_CONFIG = {
  unsupported_transport: {
    label: "Unsupported transport",
    helpText: "Configured transport is not supported by the target node.",
    statusClass: "ui-status-pill--error",
  },
  unauthorized: {
    label: "Unauthorized",
    helpText: "Credentials were rejected by the node API.",
    statusClass: "ui-status-pill--error",
  },
  no_response: {
    label: "No response",
    helpText: "Node did not return a valid status response.",
    statusClass: "ui-status-pill--error",
  },
  partial_probe: {
    label: "Partial probe",
    helpText: "Node responded, but readiness or probe checks are incomplete.",
    statusClass: "ui-status-pill--neutral",
  },
  degraded: {
    label: "Degraded",
    helpText: "Node is reachable but reports a degraded state.",
    statusClass: "ui-status-pill--neutral",
  },
  healthy: {
    label: "Healthy",
    helpText: "Node is ready and healthy.",
    statusClass: "ui-status-pill--success",
  },
};

function normalizeNodeStatusError(error = {}) {
  return {
    status: "error",
    stream_available: false,
    error_code: error.code || "UNKNOWN_ERROR",
    error_message: error.message || "Node status request failed.",
    error_details: error.details || null,
  };
}

function isFailureStatus(status = {}) {
  if (status.error_code) {
    return true;
  }

  const normalized = String(status.status || "unknown").toLowerCase();
  return ["error", "failed", "down", "unhealthy", "unauthorized"].includes(normalized);
}

function enrichStatusWithAggregation(nodeId, status = {}) {
  const existing = nodeStatusAggregationMap.get(nodeId) || {
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

  nodeStatusAggregationMap.set(nodeId, next);
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
      title: "Node target is blocked by SSRF protection.",
      hint: "Use docker network hostname (e.g., 'motion-in-ocean-webcam:8000') or enable MOTION_IN_OCEAN_ALLOW_PRIVATE_IPS. Click Diagnose for details.",
    },
    NETWORK_UNREACHABLE: {
      title: "Node is unreachable on the network.",
      hint: "Check node is running, network connectivity, and firewall rules. Click Diagnose for details.",
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
    NODE_UNREACHABLE: {
      title: "Node is unreachable.",
      hint: "Check the node base URL, networking, and that the node service is running.",
    },
    NODE_UNAUTHORIZED: {
      title: "Node rejected credentials.",
      hint: "Update node auth settings or bearer token and refresh.",
    },
    NODE_INVALID_RESPONSE: {
      title: "Node returned an invalid response.",
      hint: "Verify the node API version and status endpoint compatibility.",
    },
    TRANSPORT_UNSUPPORTED: {
      title: "Configured transport is unsupported.",
      hint: "Switch to a supported transport for this node.",
    },
    NODE_API_MISMATCH: {
      title: "Node API does not match expected management endpoints.",
      hint: "Confirm the node is running the compatible management service and exposes /api/status.",
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

function normalizeNodeStatusForUi(status = {}) {
  const statusText = String(status.status || "unknown").toLowerCase();
  const errorCode = String(status.error_code || "").toUpperCase();
  const isReady = status.ready === true;

  let subtype = "no_response";

  if (errorCode === "TRANSPORT_UNSUPPORTED") {
    subtype = "unsupported_transport";
  } else if (errorCode === "NODE_API_MISMATCH") {
    subtype = "no_response";
  } else if (errorCode === "NODE_UNAUTHORIZED" || statusText === "unauthorized") {
    subtype = "unauthorized";
  } else if (statusText === "ok" || statusText === "healthy" || statusText === "ready") {
    subtype = isReady ? "healthy" : "partial_probe";
  } else if (statusText === "degraded" || statusText === "warning") {
    subtype = "degraded";
  } else if (statusText === "partial" || statusText === "probing") {
    subtype = "partial_probe";
  } else if (statusText === "error" || statusText === "failed" || statusText === "down") {
    subtype = "no_response";
  }

  const config = STATUS_SUBTYPE_CONFIG[subtype] || {
    label: "Unknown",
    helpText: "Node state is unknown.",
    statusClass: statusClass(statusText),
  };

  let reasonText = getStatusReason(status);
  if (subtype === "healthy") {
    reasonText = "Ready and responding.";
  } else if (subtype === "partial_probe") {
    reasonText = status.error_message || "Node responded, but readiness is incomplete.";
  } else if (subtype === "degraded") {
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

function renderRows() {
  if (!nodes.length) {
    tableBody.innerHTML = '<tr><td colspan="7" class="empty">No nodes registered.</td></tr>';
    return;
  }

  const escapeHtml = (str) => {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  };

  tableBody.innerHTML = nodes
    .map((node) => {
      const status = nodeStatusMap.get(node.id) || { status: "unknown", stream_available: false };
      const normalizedStatus = normalizeNodeStatusForUi(status);
      const streamText = status.stream_available ? "Available" : "Unavailable";
      const detailsText = normalizedStatus.reasonText;
      const aggregateDetails = formatAggregationDetails(status);
      const detailsTooltip = [normalizedStatus.helpText, status.error_details]
        .filter(Boolean)
        .join(" ");
      return `
        <tr>
          <td><strong>${escapeHtml(node.name)}</strong><br><small>${escapeHtml(node.id)}</small></td>
          <td>${escapeHtml(node.base_url)}</td>
          <td>${escapeHtml(node.transport)}</td>
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
              <button class="ui-btn ui-btn--danger" data-action="delete" data-id="${escapeHtml(node.id)}">Remove</button>
            </div>
          </td>
        </tr>
      `;
    })
    .join("");
}

async function fetchNodes() {
  try {
    const response = await managementFetch("/api/nodes");
    if (!response.ok) {
      throw new Error("Failed to load nodes");
    }
    const payload = await response.json();
    nodes = payload.nodes || [];
    const activeNodeIds = new Set(nodes.map((node) => node.id));
    for (const nodeId of nodeStatusMap.keys()) {
      if (!activeNodeIds.has(nodeId)) {
        nodeStatusMap.delete(nodeId);
        nodeStatusAggregationMap.delete(nodeId);
      }
    }
    renderRows();
  } catch (error) {
    if (error?.isUnauthorized) {
      showFeedback(API_AUTH_HINT, true);
    } else {
      showFeedback(error.message || "Failed to load nodes", true);
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
        nodes.map(async (node) => {
          try {
            const response = await managementFetch(
              `/api/nodes/${encodeURIComponent(node.id)}/status`,
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
                enrichStatusWithAggregation(node.id, normalizeNodeStatusError(errorPayload)),
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
                normalizeNodeStatusError({ message: error?.message || "Failed to refresh node status." }),
              ),
            );
          }
        }),
      );

      if (currentToken === statusRefreshToken) {
        nodeStatusMap = nextStatusMap;
        renderRows();
      }
    } while (statusRefreshPending);
  } finally {
    statusRefreshInFlight = false;
  }
}

function resetForm() {
  nodeForm.reset();
  editingNodeIdInput.value = "";
  formTitle.textContent = "Add node";
  document.getElementById("node-id").disabled = false;
  cancelEditBtn.classList.add("hidden");
}

async function submitNodeForm(event) {
  event.preventDefault();
  showFeedback("");

  const editingNodeId = editingNodeIdInput.value;
  const isEdit = Boolean(editingNodeId);

  let payload;
  try {
    payload = buildNodePayload({ preserveLastSeen: isEdit });
  } catch {
    showFeedback("Labels must be valid JSON.", true);
    return;
  }

  const endpoint = isEdit ? `/api/nodes/${encodeURIComponent(editingNodeId)}` : "/api/nodes";
  const method = isEdit ? "PUT" : "POST";

  try {
    const response = await managementFetch(endpoint, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorPayload = await response.json().catch(() => ({}));
      const message = errorPayload?.error?.message || "Request failed.";
      showFeedback(message, true);
      return;
    }

    showFeedback(isEdit ? "Node updated." : "Node added.");
    resetForm();
    await fetchNodes();
    await refreshStatuses();
  } catch (error) {
    if (error?.isUnauthorized) {
      showFeedback(API_AUTH_HINT, true);
      return;
    }
    showFeedback(error.message || "Network error occurred.", true);
  }
}

function beginEditNode(nodeId) {
  const node = nodes.find((entry) => entry.id === nodeId);
  if (!node) {
    return;
  }

  editingNodeIdInput.value = node.id;
  formTitle.textContent = `Edit node: ${node.id}`;
  document.getElementById("node-id").value = node.id;
  document.getElementById("node-id").disabled = true;
  document.getElementById("node-name").value = node.name || "";
  document.getElementById("node-base-url").value = node.base_url || "";
  document.getElementById("node-transport").value = node.transport || "http";
  document.getElementById("node-auth-type").value = node.auth?.type || "none";
  document.getElementById("node-auth-token").value = node.auth?.token || "";
  document.getElementById("node-capabilities").value = (node.capabilities || []).join(", ");
  document.getElementById("node-labels").value = JSON.stringify(node.labels || {}, null, 2);
  cancelEditBtn.classList.remove("hidden");
}

async function diagnoseNode(nodeId) {
  try {
    const response = await managementFetch(`/api/nodes/${encodeURIComponent(nodeId)}/diagnose`);
    if (!response.ok) {
      const errorPayload = await response.json().catch(() => ({}));
      showFeedback(errorPayload?.error?.message || "Diagnostic request failed", true);
      return;
    }

    const diagnosticResult = await response.json();
    showDiagnosticResults(diagnosticResult);
  } catch (error) {
    if (error?.isUnauthorized) {
      showFeedback(API_AUTH_HINT, true);
      return;
    }
    showFeedback(error.message || "Network error occurred.", true);
  }
}

function showDiagnosticResults(diagnosticResult) {
  const nodeId = diagnosticResult.node_id;
  const diagnostics = diagnosticResult.diagnostics || {};
  const guidance = diagnosticResult.guidance || [];
  
  let message = `Diagnostic Report for ${nodeId}\n\n`;
  
  // Registration check
  if (!diagnostics.registration?.valid) {
    message += "❌ Registration: Invalid\n";
    if (diagnostics.registration?.error) {
      message += `   Error: ${diagnostics.registration.error}\n`;
    }
  } else {
    message += "✓ Registration: Valid\n";
  }
  
  // URL validation check
  if (diagnostics.url_validation?.blocked) {
    message += `❌ URL Validation: Blocked\n`;
    if (diagnostics.url_validation?.blocked_reason) {
      message += `   Reason: ${diagnostics.url_validation.blocked_reason}\n`;
    }
  } else {
    message += "✓ URL Validation: Passed\n";
  }
  
  // DNS resolution
  if (!diagnostics.dns_resolution?.resolves) {
    message += `❌ DNS Resolution: Failed\n`;
    if (diagnostics.dns_resolution?.error) {
      message += `   Error: ${diagnostics.dns_resolution.error}\n`;
    }
  } else {
    message += "✓ DNS Resolution: Success\n";
    if (diagnostics.dns_resolution?.resolved_ips?.length > 0) {
      message += `   IPs: ${diagnostics.dns_resolution.resolved_ips.join(", ")}\n`;
    }
  }
  
  // Network connectivity
  if (!diagnostics.network_connectivity?.reachable) {
    message += `❌ Network Connectivity: Unreachable\n`;
    if (diagnostics.network_connectivity?.error) {
      message += `   Error: ${diagnostics.network_connectivity.error}\n`;
    }
    if (diagnostics.network_connectivity?.category) {
      message += `   Category: ${diagnostics.network_connectivity.category}\n`;
    }
  } else {
    message += "✓ Network Connectivity: Reachable\n";
  }
  
  // API endpoint
  if (diagnostics.api_endpoint?.status_code) {
    message += `✓ API Endpoint (/api/status): HTTP ${diagnostics.api_endpoint.status_code}\n`;
    if (diagnostics.api_endpoint?.healthy === false && diagnostics.api_endpoint?.status_code === 503) {
      message += "   Node is reachable but returning 503 (may be initializing)\n";
    }
  } else if (!diagnostics.api_endpoint?.accessible) {
    message += `❌ API Endpoint (/api/status): Not Accessible\n`;
    if (diagnostics.api_endpoint?.error) {
      message += `   Error: ${diagnostics.api_endpoint.error}\n`;
    }
  }
  
  // Guidance
  if (guidance.length > 0) {
    message += `\nRecommendations:\n`;
    guidance.forEach((rec) => {
      if (rec.includes("✓")) {
        message += `  ${rec}\n`;
      } else if (rec.includes("WARNING:")) {
        message += `  ⚠️  ${rec}\n`;
      } else {
        message += `  → ${rec}\n`;
      }
    });
  }
  
  // Show in alert (and copy to clipboard)
  alert(message);
  
  // Also try to copy to clipboard
  navigator.clipboard.writeText(message).catch(() => {
    // Silently fail if clipboard API not available
  });
}

async function removeNode(nodeId) {
  if (!window.confirm(`Delete node ${nodeId}?`)) {
    return;
  }

  try {
    const response = await managementFetch(`/api/nodes/${encodeURIComponent(nodeId)}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      const errorPayload = await response.json().catch(() => ({}));
      showFeedback(errorPayload?.error?.message || "Delete failed", true);
      return;
    }

    showFeedback(`Node ${nodeId} removed.`);
    if (editingNodeIdInput.value === nodeId) {
      resetForm();
    }
    await fetchNodes();
    await refreshStatuses();
  } catch (error) {
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
  } else if (action === "delete") {
    removeNode(nodeId);
  } else if (action === "diagnose") {
    diagnoseNode(nodeId);
  }
}

async function init() {
  nodeForm.addEventListener("submit", submitNodeForm);
  cancelEditBtn.addEventListener("click", () => {
    resetForm();
    showFeedback("");
  });
  refreshBtn.addEventListener("click", async () => {
    stopStatusRefreshInterval();
    await fetchNodes();
    await refreshStatuses();
    startStatusRefreshInterval();
    showFeedback("Node list refreshed.");
  });
  tableBody.addEventListener("click", onTableClick);

  await fetchNodes();
  await refreshStatuses();
  startStatusRefreshInterval();
}

init().catch((error) => {
  showFeedback(error.message || "Failed to load management data.", true);
});
