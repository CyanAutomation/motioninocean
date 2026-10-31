import test from "node:test";
import assert from "node:assert/strict";
import {
  refreshConfigPanel,
  startConfigPolling,
  type ConfigPollingDependencies,
} from "../../frontend/src/config-polling.ts";

test("configuration polling schedules recurring updates at the documented cadence", () => {
  // Traceability: docs/product/PRD-frontend.md, config polling interval.
  let scheduledCallback: (() => void) | undefined;
  let scheduledDelay = 0;
  let updates = 0;
  const intervalHandle = setInterval(() => {}, 60_000);
  const state = {
    configInitialLoadPending: false,
    configPollingInterval: null as ReturnType<typeof setInterval> | null,
  };

  startConfigPolling(state, {
    updateConfig: async () => {
      updates += 1;
    },
    logError: () => {},
    scheduleInterval: (callback, delayMs) => {
      scheduledCallback = callback;
      scheduledDelay = delayMs;
      return intervalHandle;
    },
  });

  assert.equal(scheduledDelay, 5000);
  scheduledCallback?.();
  assert.equal(updates, 1);
  clearInterval(intervalHandle);
});

test("refreshConfigPanel marks initial load pending and requests config update", async () => {
  let updateCalls = 0;
  const state = {
    configInitialLoadPending: false,
    configPollingInterval: null as ReturnType<typeof setInterval> | null,
  };
  const dependencies: ConfigPollingDependencies = {
    updateConfig: async () => {
      updateCalls += 1;
    },
    logError: () => {},
  };

  refreshConfigPanel(state, dependencies);
  await Promise.resolve();

  assert.equal(state.configInitialLoadPending, true);
  assert.equal(updateCalls, 1);
});
