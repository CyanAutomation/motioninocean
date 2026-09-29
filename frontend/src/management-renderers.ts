export interface WebcamSummary {
  total_webcams?: number | null;
  healthy_webcams?: number | null;
  unavailable_webcams?: number | null;
  stream_available_webcams?: number | null;
}

export interface ActivityEntry {
  timestamp: string;
  message: string;
}

export interface OverviewStatus {
  error_code?: unknown;
}

interface TextElement {
  textContent: string;
}

interface HtmlElement {
  innerHTML: string;
}

interface ButtonElement {
  disabled: boolean;
}

export interface OverviewPanelContext {
  snapshot: WebcamSummary | null;
  activityFeed: readonly ActivityEntry[];
  statuses: ReadonlyMap<string, OverviewStatus>;
  pendingDiscoveryCount: number;
  totalElement: TextElement | null;
  healthyElement: TextElement | null;
  unavailableElement: TextElement | null;
  streamingElement: TextElement | null;
  activityElement: HtmlElement | null;
  actionElement: HtmlElement | null;
  escapeHtml: (value: unknown) => string;
}

export interface DiscoveredNode {
  id: string;
  name?: string;
  base_url?: string;
}

export interface DiscoveredNodeStatus {
  error_message?: unknown;
  error_details?: unknown;
}

export interface DiscoveredPanelContext {
  nodes: readonly DiscoveredNode[];
  snoozedIds: ReadonlySet<string>;
  selectedNodeId: string;
  statuses: ReadonlyMap<string, DiscoveredNodeStatus>;
  listElement: HtmlElement | null;
  notesElement: HtmlElement | null;
  actionButtons: readonly (ButtonElement | null)[];
  escapeHtml: (value: unknown) => string;
}

/**
 * Render overview metrics, recent activity, and pending action summaries.
 *
 * @param context - Dashboard data, DOM targets, and text escaping function.
 * @returns Nothing.
 */
export function renderOverviewPanel(context: OverviewPanelContext): void {
  renderSummary(context);
  renderActivity(context);
  renderActions(context);
}

function renderSummary(context: OverviewPanelContext): void {
  if (!context.snapshot) return;
  setText(context.totalElement, context.snapshot.total_webcams);
  setText(context.healthyElement, context.snapshot.healthy_webcams);
  setText(context.unavailableElement, context.snapshot.unavailable_webcams);
  setText(context.streamingElement, context.snapshot.stream_available_webcams);
}

function setText(element: TextElement | null, value: number | null | undefined): void {
  if (element) element.textContent = String(value ?? 0);
}

function renderActivity(context: OverviewPanelContext): void {
  if (!context.activityElement) return;
  const items = context.activityFeed.map((entry) => {
    const time = context.escapeHtml(new Date(entry.timestamp).toLocaleTimeString());
    const message = context.escapeHtml(entry.message);
    return `<li><strong>${time}</strong> ${message}</li>`;
  });
  context.activityElement.innerHTML = items.length ? items.join("") : "<li>No activity yet.</li>";
}

function renderActions(context: OverviewPanelContext): void {
  if (!context.actionElement) return;
  const issues = countActionableStatuses(context.statuses);
  const items = createActionItems(issues, context.pendingDiscoveryCount);
  context.actionElement.innerHTML = items.length
    ? items.map((item) => `<li>${context.escapeHtml(item)}</li>`).join("")
    : "<li>No action items.</li>";
}

function countActionableStatuses(statuses: ReadonlyMap<string, OverviewStatus>): {
  auth: number;
  privateAddress: number;
} {
  let auth = 0;
  let privateAddress = 0;
  statuses.forEach((status) => {
    const code = String(status.error_code || "").toUpperCase();
    if (code === "WEBCAM_UNAUTHORIZED") auth += 1;
    if (code === "SSRF_BLOCKED") privateAddress += 1;
  });
  return { auth, privateAddress };
}

function createActionItems(
  issues: { auth: number; privateAddress: number },
  pendingDiscoveryCount: number,
): string[] {
  const items: string[] = [];
  if (issues.auth > 0) items.push(`Auth remediation needed on ${issues.auth} node(s).`);
  if (pendingDiscoveryCount > 0) {
    items.push(`${pendingDiscoveryCount} discovered device(s) waiting for review.`);
  }
  if (issues.privateAddress > 0) {
    items.push(`${issues.privateAddress} node(s) blocked by safety rules.`);
  }
  return items;
}

/**
 * Render pending discovery nodes and return the selected visible node id.
 *
 * @param context - Nodes, statuses, controls, and DOM targets for the panel.
 * @returns The selected visible node id, or an empty string when no node is pending.
 */
export function renderDiscoveredPanel(context: DiscoveredPanelContext): string {
  const pendingNodes = getPendingNodes(context.nodes, context.snoozedIds);
  const selectedNodeId = resolveSelectedNode(pendingNodes, context.selectedNodeId);
  renderDiscoveredList(pendingNodes, selectedNodeId, context);
  renderDiscoveredNotes(selectedNodeId, context);
  updateDecisionButtons(selectedNodeId, context.actionButtons);
  return selectedNodeId;
}

function getPendingNodes(
  nodes: readonly DiscoveredNode[],
  snoozedIds: ReadonlySet<string>,
): DiscoveredNode[] {
  return nodes.filter((node) => !snoozedIds.has(node.id));
}

function resolveSelectedNode(nodes: readonly DiscoveredNode[], selectedNodeId: string): string {
  if (nodes.some((node) => node.id === selectedNodeId)) return selectedNodeId;
  return nodes[0]?.id || "";
}

function renderDiscoveredList(
  nodes: readonly DiscoveredNode[],
  selectedNodeId: string,
  context: DiscoveredPanelContext,
): void {
  if (!context.listElement) return;
  if (nodes.length === 0) {
    context.listElement.innerHTML = "<li>No discovered devices pending approval.</li>";
    return;
  }
  context.listElement.innerHTML = nodes
    .map((node) => renderDiscoveredNode(node, selectedNodeId, context.escapeHtml))
    .join("");
}

function renderDiscoveredNode(
  node: DiscoveredNode,
  selectedNodeId: string,
  escapeHtml: (value: unknown) => string,
): string {
  const selectedClass = node.id === selectedNodeId ? " discovered-item--selected" : "";
  const name = escapeHtml(node.name || node.id);
  const id = escapeHtml(node.id);
  const baseUrl = escapeHtml(node.base_url || "Unknown URL");
  return `<li>
    <button class="discovered-item${selectedClass}" data-discovered-id="${id}" type="button">
      <strong>${name}</strong><br/>
      <small>${baseUrl}</small>
    </button>
  </li>`;
}

function renderDiscoveredNotes(selectedNodeId: string, context: DiscoveredPanelContext): void {
  if (!context.notesElement) return;
  const status = context.statuses.get(selectedNodeId);
  const notes = getDiscoveryNotes(status);
  context.notesElement.innerHTML = notes
    .map((note) => `<li>${context.escapeHtml(note)}</li>`)
    .join("");
}

function getDiscoveryNotes(status: DiscoveredNodeStatus | undefined): string[] {
  const notes: string[] = [];
  if (status?.error_message) notes.push(String(status.error_message));
  if (status?.error_details) notes.push(String(status.error_details));
  return notes.length ? notes : ["Blocked by local safety rule."];
}

function updateDecisionButtons(
  selectedNodeId: string,
  buttons: readonly (ButtonElement | null)[],
): void {
  buttons.forEach((button) => {
    if (button) button.disabled = !selectedNodeId;
  });
}
