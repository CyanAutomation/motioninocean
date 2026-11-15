import { formatAggregationDetails, formatDateTime, getDiscoveryInfo, normalizeWebcamStatusForUi, } from "./management-domain.js";
import { escapeHtml } from "./html.js";
/** Render the registered webcam rows, including status and discovery actions. */
export function renderWebcamRows({ webcams, statuses }) {
    if (webcams.length === 0) {
        return `
      <tr><td colspan="4" class="empty">No webcam hosts yet. Add a webcam to start monitoring it.</td></tr>
    `;
    }
    const rows = webcams.map((node) => {
        const status = statuses.get(node.id) || { status: "unknown", stream_available: false };
        const normalizedStatus = normalizeWebcamStatusForUi(status);
        const streamText = status.stream_available ? "Available" : "Unavailable";
        const discovery = getDiscoveryInfo(node);
        const aggregateDetails = formatAggregationDetails(status);
        const approvalHint = discovery.source === "discovered" && !discovery.approved
            ? "Pending approval before full activation."
            : "";
        const detailsText = [approvalHint, normalizedStatus.reasonText].filter(Boolean).join(" ");
        const filterStatus = normalizedStatus.subtype === "healthy" ? "online" : "needs-attention";
        const searchText = [node.name, node.id, node.base_url].filter(Boolean).join(" ");
        return `
      <tr
        data-webcam-row
        data-search="${escapeHtml(searchText)}"
        data-status="${filterStatus}"
      >
        <td>
          <strong>${escapeHtml(node.name)}</strong><br><small>${escapeHtml(node.id)}</small>
          <details class="node-row-details">
            <summary>Node details</summary>
            <dl>
              <div><dt>Address</dt><dd>${escapeHtml(node.base_url)}</dd></div>
              <div><dt>Transport</dt><dd>${escapeHtml(node.transport)}</dd></div>
              <div><dt>Source</dt><dd>${escapeHtml(discovery.source)}</dd></div>
              <div><dt>Approval</dt><dd>${escapeHtml(discovery.approved ? "Approved" : "Pending")}</dd></div>
              <div><dt>First seen</dt><dd>${escapeHtml(formatDateTime(discovery.firstSeen))}</dd></div>
              <div><dt>Last announcement</dt><dd>${escapeHtml(formatDateTime(discovery.lastAnnounceAt))}</dd></div>
              <div><dt>Connection details</dt><dd>${escapeHtml(detailsText || normalizedStatus.helpText)}</dd></div>
              ${status.error_details ? `<div><dt>Diagnostic detail</dt><dd>${escapeHtml(status.error_details)}</dd></div>` : ""}
              ${aggregateDetails ? `<div><dt>Status history</dt><dd>${escapeHtml(aggregateDetails)}</dd></div>` : ""}
            </dl>
          </details>
        </td>
        <td>
          <span class="ui-badge ${getStatusBadgeClass(normalizedStatus.statusClass)}" title="${escapeHtml(normalizedStatus.helpText)}">${escapeHtml(normalizedStatus.label)}</span>
        </td>
        <td>${streamText}</td>
        <td>
          <div class="row-actions">
            <button class="ui-btn ui-btn--secondary" type="button" data-action="edit" data-id="${escapeHtml(node.id)}">Edit</button>
            <button class="ui-btn ui-btn--secondary" type="button" data-action="diagnose" data-id="${escapeHtml(node.id)}">Diagnose</button>
            ${discovery.source === "discovered" ? `<button class="ui-btn ui-btn--secondary" type="button" data-action="approve" data-id="${escapeHtml(node.id)}">Approve</button><button class="ui-btn ui-btn--secondary" type="button" data-action="reject" data-id="${escapeHtml(node.id)}">Reject</button>` : ""}
            <button class="ui-btn ui-btn--danger" type="button" data-action="delete" data-id="${escapeHtml(node.id)}">Remove</button>
          </div>
        </td>
      </tr>
    `;
    });
    return (rows.join("") +
        `<tr id="webcams-no-match-row" hidden><td colspan="4" class="empty">No webcams match these filters. Try another search or status.</td></tr>`);
}
function getStatusBadgeClass(statusClassName) {
    if (statusClassName.includes("success"))
        return "ui-badge--success";
    if (statusClassName.includes("error"))
        return "ui-badge--danger";
    return "ui-badge--neutral";
}
