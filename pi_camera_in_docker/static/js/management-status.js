/**
 * Record status updates and report transitions to the activity feed.
 *
 * @param nextStatuses - Status values produced by the latest poll.
 * @param history - Previous statuses, updated in place.
 * @param appendActivityFeed - Callback that records user-visible status events.
 * @returns Nothing.
 */
export function recordStatusHistory(nextStatuses, history, appendActivityFeed) {
    nextStatuses.forEach((nextStatus, nodeId) => {
        const previous = history.get(nodeId);
        getStatusEvents(nodeId, previous, nextStatus).forEach(({ message, level }) => {
            emitStatusEvent(appendActivityFeed, message, level);
        });
        history.set(nodeId, nextStatus);
    });
}
function emitStatusEvent(appendActivityFeed, message, level) {
    if (level)
        appendActivityFeed(message, level);
    else
        appendActivityFeed(message);
}
function getStatusEvents(nodeId, previous, next) {
    const nextCode = normalizeCode(next.error_code);
    const nextState = normalizeState(next.status);
    const previousCode = normalizeCode(previous?.error_code);
    const previousState = normalizeState(previous?.status);
    const events = [];
    if (!previous) {
        events.push({ message: `${nodeId} status initialized: ${nextState}.` });
    }
    else if (didStatusChange(previousCode, previousState, nextCode, nextState)) {
        events.push({ message: `${nodeId} status changed to ${nextCode || nextState}.` });
    }
    if (previous && previousCode && !nextCode) {
        events.push({ message: `${nodeId} recovered.`, level: "success" });
    }
    return events;
}
function normalizeCode(value) {
    return String(value || "").toUpperCase();
}
function normalizeState(value) {
    return String(value || "unknown").toLowerCase();
}
function didStatusChange(previousCode, previousState, nextCode, nextState) {
    return ((previousCode !== nextCode && Boolean(nextCode)) ||
        (previousState !== nextState && nextState !== "unknown"));
}
/**
 * Create a status refresh coordinator that coalesces overlapping polls.
 *
 * @param dependencies - Data access, rendering, and feedback callbacks.
 * @returns A refresh function suitable for manual and interval-triggered calls.
 */
export function createStatusRefresher(dependencies) {
    const state = { inFlight: false, pending: false, pendingManual: false, token: 0 };
    return async function refreshStatuses(options = {}) {
        const fromInterval = options.fromInterval ?? false;
        if (queueRefreshIfBusy(state, fromInterval))
            return;
        state.inFlight = true;
        try {
            await runPendingRefreshes(state, dependencies, !fromInterval);
        }
        finally {
            state.inFlight = false;
        }
    };
}
function queueRefreshIfBusy(state, fromInterval) {
    if (!state.inFlight)
        return false;
    state.pending = true;
    if (!fromInterval)
        state.pendingManual = true;
    return true;
}
async function runPendingRefreshes(state, dependencies, initialManualFeedback) {
    let allowManualFeedback = initialManualFeedback;
    do {
        state.pending = false;
        allowManualFeedback = allowManualFeedback || state.pendingManual;
        state.pendingManual = false;
        await runRefreshCycle(state, dependencies, allowManualFeedback);
    } while (state.pending);
}
async function runRefreshCycle(state, dependencies, allowManualFeedback) {
    const token = ++state.token;
    const datasetVersion = dependencies.getDatasetVersion();
    const nodeIds = new Set(dependencies.getNodes().map((node) => node.id));
    let feedbackShown = false;
    const statuses = await dependencies.fetchStatusesForNodes(nodeIds, allowManualFeedback, () => {
        if (feedbackShown)
            return;
        dependencies.showUnauthorizedFeedback();
        feedbackShown = true;
    });
    if (!isCurrentRefresh(state, dependencies, token, datasetVersion))
        return;
    const filteredStatuses = filterRemovedNodes(statuses, dependencies.getNodes());
    recordStatusHistory(filteredStatuses, dependencies.getStatusHistory(), dependencies.appendActivityFeed);
    dependencies.setStatuses(filteredStatuses);
    renderPanels(dependencies);
}
function isCurrentRefresh(state, dependencies, token, datasetVersion) {
    return token === state.token && datasetVersion === dependencies.getDatasetVersion();
}
function filterRemovedNodes(statuses, currentNodes) {
    const activeNodeIds = new Set(currentNodes.map((node) => node.id));
    return new Map(Array.from(statuses).filter(([nodeId]) => activeNodeIds.has(nodeId)));
}
function renderPanels(dependencies) {
    dependencies.renderRows();
    dependencies.renderDiscoveredPanel();
    dependencies.renderOverviewPanel();
}
