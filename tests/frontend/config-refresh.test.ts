import test from "node:test";
import assert from "node:assert/strict";
import {
  CONFIG_POLL_INTERVAL_MS,
  refreshConfigPanel,
  type ConfigPollingDependencies,
} from "../../frontend/src/config-polling.ts";

test("configuration polling uses a lower-cost 15 second cadence", () => {
  assert.equal(CONFIG_POLL_INTERVAL_MS, 15000);
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
