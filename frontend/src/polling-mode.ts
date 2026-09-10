/** Active frontend polling mechanisms. */
export interface PollingState {
  sse: boolean;
  config: boolean;
  timestamp: boolean;
}

/** Assertion callback used to report an invalid polling state. */
export type PollingModeAssertion = (condition: boolean, message: string) => void;

/** Operator-facing diagnostic shown when polling mechanisms overlap. */
export const POLLING_MODE_ASSERTION_MESSAGE =
  "Invalid polling state: SSE, config polling, and timestamp polling are mutually exclusive.";

/**
 * Validate that no more than one polling mechanism is active.
 *
 * @param pollingState - Active state for every polling mechanism.
 * @param emitAssertion - Assertion callback used to report the validation result.
 * @returns Whether the polling state is valid.
 */
export function assertSinglePollingMode(
  pollingState: PollingState,
  emitAssertion: PollingModeAssertion = (condition, message) => console.assert(condition, message),
): boolean {
  const activeModeCount = Object.values(pollingState).filter(Boolean).length;
  const valid = activeModeCount <= 1;

  emitAssertion(valid, POLLING_MODE_ASSERTION_MESSAGE);
  return valid;
}
