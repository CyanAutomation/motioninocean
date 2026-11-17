import { isRequestTimeoutError } from "./fetch-json.js";

/** Callbacks for the retryable-timeout and failed-request paths. */
export interface StatsUpdateErrorHandlers {
  onTimeout: () => void;
  onFailure: (error: unknown) => void;
}

/**
 * Route a stats request error to retry or connection failure handling.
 *
 * @param error - Error caught while fetching stats.
 * @param handlers - Actions for retryable timeout and ordinary failure cases.
 * @returns Nothing; invokes exactly one matching handler.
 */
export function handleStatsUpdateFailure(
  error: unknown,
  handlers: StatsUpdateErrorHandlers,
): void {
  if (isRequestTimeoutError(error)) {
    handlers.onTimeout();
    return;
  }

  handlers.onFailure(error);
}
