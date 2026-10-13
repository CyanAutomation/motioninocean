export const CONFIG_POLL_INTERVAL_MS = 5000;
/** Start one recurring configuration refresh, if polling is not already active. */
export function startConfigPolling(state, dependencies) {
    if (state.configPollingInterval)
        return;
    const scheduleInterval = dependencies.scheduleInterval ?? ((callback, delayMs) => setInterval(callback, delayMs));
    state.configPollingInterval = scheduleInterval(() => {
        void dependencies.updateConfig().catch((error) => {
            dependencies.logError("Config update failed:", error);
        });
    }, CONFIG_POLL_INTERVAL_MS);
}
/** Mark configuration as an initial load and immediately request an update. */
export function refreshConfigPanel(state, dependencies) {
    state.configInitialLoadPending = true;
    void dependencies.updateConfig().catch((error) => {
        dependencies.logError("Config update failed:", error);
    });
}
