export const CONFIG_POLL_INTERVAL_MS = 5000;

export interface ConfigPollingState {
  configPollingInterval: ReturnType<typeof setInterval> | null;
  configInitialLoadPending: boolean;
}

export interface ConfigPollingDependencies {
  updateConfig: () => Promise<void>;
  logError: (message: string, error: unknown) => void;
  scheduleInterval?: (callback: () => void, delayMs: number) => ReturnType<typeof setInterval>;
}

/** Start one recurring configuration refresh, if polling is not already active. */
export function startConfigPolling(
  state: ConfigPollingState,
  dependencies: ConfigPollingDependencies,
): void {
  if (state.configPollingInterval) return;

  const scheduleInterval =
    dependencies.scheduleInterval ?? ((callback, delayMs) => setInterval(callback, delayMs));
  state.configPollingInterval = scheduleInterval(() => {
    void dependencies.updateConfig().catch((error: unknown) => {
      dependencies.logError("Config update failed:", error);
    });
  }, CONFIG_POLL_INTERVAL_MS);
}

/** Mark configuration as an initial load and immediately request an update. */
export function refreshConfigPanel(
  state: ConfigPollingState,
  dependencies: ConfigPollingDependencies,
): void {
  state.configInitialLoadPending = true;
  void dependencies.updateConfig().catch((error: unknown) => {
    dependencies.logError("Config update failed:", error);
  });
}
