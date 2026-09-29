export interface WebcamNode {
  id: string;
}

export interface NodeStatus {
  status?: unknown;
  error_code?: unknown;
  [key: string]: unknown;
}

export interface StatusRefreshOptions {
  fromInterval?: boolean;
}

export interface StatusRefreshDependencies {
  getNodes: () => readonly WebcamNode[];
  getDatasetVersion: () => number;
  getStatusHistory: () => Map<string, NodeStatus>;
  fetchStatusesForNodes: (
    nodeIds: Set<string>,
    allowManualFeedback: boolean,
    onUnauthorized: () => void,
  ) => Promise<Map<string, NodeStatus>>;
  setStatuses: (statuses: Map<string, NodeStatus>) => void;
  showUnauthorizedFeedback: () => void;
  renderRows: () => void;
  renderDiscoveredPanel: () => void;
  renderOverviewPanel: () => void;
  appendActivityFeed: (message: string, level?: string) => void;
}

interface RefreshState {
  inFlight: boolean;
  pending: boolean;
  pendingManual: boolean;
  token: number;
}

/**
 * Record status updates and report transitions to the activity feed.
 *
 * @param nextStatuses - Status values produced by the latest poll.
 * @param history - Previous statuses, updated in place.
 * @param appendActivityFeed - Callback that records user-visible status events.
 * @returns Nothing.
 */
export function recordStatusHistory(
  nextStatuses: Map<string, NodeStatus>,
  history: Map<string, NodeStatus>,
  appendActivityFeed: (message: string, level?: string) => void,
): void {
  nextStatuses.forEach((nextStatus, nodeId) => {
    const previous = history.get(nodeId);
    getStatusEvents(nodeId, previous, nextStatus).forEach(({ message, level }) => {
      emitStatusEvent(appendActivityFeed, message, level);
    });
    history.set(nodeId, nextStatus);
  });
}

function emitStatusEvent(
  appendActivityFeed: (message: string, level?: string) => void,
  message: string,
  level?: string,
): void {
  if (level) appendActivityFeed(message, level);
  else appendActivityFeed(message);
}

function getStatusEvents(
  nodeId: string,
  previous: NodeStatus | undefined,
  next: NodeStatus,
): Array<{ message: string; level?: string }> {
  const nextCode = normalizeCode(next.error_code);
  const nextState = normalizeState(next.status);
  const previousCode = normalizeCode(previous?.error_code);
  const previousState = normalizeState(previous?.status);
  const events: Array<{ message: string; level?: string }> = [];

  if (!previous) {
    events.push({ message: `${nodeId} status initialized: ${nextState}.` });
  } else if (didStatusChange(previousCode, previousState, nextCode, nextState)) {
    events.push({ message: `${nodeId} status changed to ${nextCode || nextState}.` });
  }
  if (previous && previousCode && !nextCode) {
    events.push({ message: `${nodeId} recovered.`, level: "success" });
  }
  return events;
}

function normalizeCode(value: unknown): string {
  return String(value || "").toUpperCase();
}

function normalizeState(value: unknown): string {
  return String(value || "unknown").toLowerCase();
}

function didStatusChange(
  previousCode: string,
  previousState: string,
  nextCode: string,
  nextState: string,
): boolean {
  return (
    (previousCode !== nextCode && Boolean(nextCode)) ||
    (previousState !== nextState && nextState !== "unknown")
  );
}

/**
 * Create a status refresh coordinator that coalesces overlapping polls.
 *
 * @param dependencies - Data access, rendering, and feedback callbacks.
 * @returns A refresh function suitable for manual and interval-triggered calls.
 */
export function createStatusRefresher(
  dependencies: StatusRefreshDependencies,
): (options?: StatusRefreshOptions) => Promise<void> {
  const state: RefreshState = { inFlight: false, pending: false, pendingManual: false, token: 0 };

  return async function refreshStatuses(options: StatusRefreshOptions = {}): Promise<void> {
    const fromInterval = options.fromInterval ?? false;
    if (queueRefreshIfBusy(state, fromInterval)) return;

    state.inFlight = true;
    try {
      await runPendingRefreshes(state, dependencies, !fromInterval);
    } finally {
      state.inFlight = false;
    }
  };
}

function queueRefreshIfBusy(state: RefreshState, fromInterval: boolean): boolean {
  if (!state.inFlight) return false;
  state.pending = true;
  if (!fromInterval) state.pendingManual = true;
  return true;
}

async function runPendingRefreshes(
  state: RefreshState,
  dependencies: StatusRefreshDependencies,
  initialManualFeedback: boolean,
): Promise<void> {
  let allowManualFeedback = initialManualFeedback;
  do {
    state.pending = false;
    allowManualFeedback = allowManualFeedback || state.pendingManual;
    state.pendingManual = false;
    await runRefreshCycle(state, dependencies, allowManualFeedback);
  } while (state.pending);
}

async function runRefreshCycle(
  state: RefreshState,
  dependencies: StatusRefreshDependencies,
  allowManualFeedback: boolean,
): Promise<void> {
  const token = ++state.token;
  const datasetVersion = dependencies.getDatasetVersion();
  const nodeIds = new Set(dependencies.getNodes().map((node) => node.id));
  let feedbackShown = false;
  const statuses = await dependencies.fetchStatusesForNodes(nodeIds, allowManualFeedback, () => {
    if (feedbackShown) return;
    dependencies.showUnauthorizedFeedback();
    feedbackShown = true;
  });

  if (!isCurrentRefresh(state, dependencies, token, datasetVersion)) return;
  const filteredStatuses = filterRemovedNodes(statuses, dependencies.getNodes());
  recordStatusHistory(
    filteredStatuses,
    dependencies.getStatusHistory(),
    dependencies.appendActivityFeed,
  );
  dependencies.setStatuses(filteredStatuses);
  renderPanels(dependencies);
}

function isCurrentRefresh(
  state: RefreshState,
  dependencies: StatusRefreshDependencies,
  token: number,
  datasetVersion: number,
): boolean {
  return token === state.token && datasetVersion === dependencies.getDatasetVersion();
}

function filterRemovedNodes(
  statuses: Map<string, NodeStatus>,
  currentNodes: readonly WebcamNode[],
): Map<string, NodeStatus> {
  const activeNodeIds = new Set(currentNodes.map((node) => node.id));
  return new Map(Array.from(statuses).filter(([nodeId]) => activeNodeIds.has(nodeId)));
}

function renderPanels(dependencies: StatusRefreshDependencies): void {
  dependencies.renderRows();
  dependencies.renderDiscoveredPanel();
  dependencies.renderOverviewPanel();
}
