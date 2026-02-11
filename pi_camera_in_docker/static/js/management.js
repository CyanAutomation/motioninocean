const tableBody = document.getElementById("nodes-table-body");
const nodeForm = document.getElementById("node-form");
const feedback = document.getElementById("form-feedback");
const formTitle = document.getElementById("form-title");
const cancelEditBtn = document.getElementById("cancel-edit-btn");
const refreshBtn = document.getElementById("refresh-nodes-btn");
const editingNodeIdInput = document.getElementById("editing-node-id");

let nodes = [];
let nodeStatusMap = new Map();
let statusRefreshInFlight = false;
let statusRefreshPending = false;
let statusRefreshPendingManual = false;
let statusRefreshToken = 0;
let statusRefreshIntervalId;
const NODE_TOKEN_HINT =
  "Node authentication failed. Check the remote node MANAGEMENT_AUTH_TOKEN and this node bearer token match.";

function showFeedback(message, isError = false) {
  feedback.textContent = message;
  feedback.style.color = isError ? "#b91c1c" : "#166534";
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
    return "status-ready";
  }
  if (["error", "down", "failed", "unhealthy"].includes(normalized)) {
    return "status-error";
  }
  return "status-unknown";
}

function renderRows() {
  if (!nodes.length) {
    tableBody.innerHTML = '<tr><td colspan="6" class="empty">No nodes registered.</td></tr>';
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
      const streamText = status.stream_available ? "Available" : "Unavailable";
      const statusText = status.status || "unknown";
      return `
        <tr>
          <td><strong>${escapeHtml(node.name)}</strong><br><small>${escapeHtml(node.id)}</small></td>
          <td>${escapeHtml(node.base_url)}</td>
          <td>${escapeHtml(node.transport)}</td>
          <td><span class="status-pill ${statusClass(statusText)}">${escapeHtml(statusText)}</span></td>
          <td>${streamText}</td>
          <td>
            <div class="row-actions">
              <button class="secondary" data-action="edit" data-id="${escapeHtml(node.id)}">Edit</button>
              <button class="danger" data-action="delete" data-id="${escapeHtml(node.id)}">Remove</button>
            </div>
          </td>
        </tr>
      `;
    })
    .join("");
}

async function fetchNodes() {
  try {
    const response = await fetch("/api/nodes");
    if (!response.ok) {
      throw new Error("Failed to load nodes");
    }
    const payload = await response.json();
    nodes = payload.nodes || [];
    renderRows();
  } catch (error) {
    showFeedback(error.message || "Failed to load nodes", true);
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
            const response = await fetch(`/api/nodes/${encodeURIComponent(node.id)}/status`);
            if (!response.ok) {
              if (allowManualFeedback && response.status === 401 && !showedUnauthorizedFeedback) {
                const errorPayload = await response.json().catch(() => ({}));
                if (errorPayload?.error?.code === "NODE_UNAUTHORIZED") {
                  showFeedback(NODE_TOKEN_HINT, true);
                  showedUnauthorizedFeedback = true;
                }
              }
              nextStatusMap.set(node.id, { status: "error", stream_available: false });
              return;
            }
            const payload = await response.json();
            nextStatusMap.set(node.id, payload);
          } catch {
            nextStatusMap.set(node.id, { status: "error", stream_available: false });
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
    const response = await fetch(endpoint, {
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

async function removeNode(nodeId) {
  if (!window.confirm(`Delete node ${nodeId}?`)) {
    return;
  }

  try {
    const response = await fetch(`/api/nodes/${encodeURIComponent(nodeId)}`, { method: "DELETE" });
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
