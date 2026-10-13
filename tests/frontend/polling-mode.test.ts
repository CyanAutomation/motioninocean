import test from "node:test";
import assert from "node:assert/strict";
import { assertSinglePollingMode } from "../../frontend/src/polling-mode.ts";
import {
  CONFIG_POLL_INTERVAL_MS,
  startConfigPolling,
  type ConfigPollingDependencies,
} from "../../frontend/src/config-polling.ts";

const pollingModeCases = [
  { name: "no polling", state: { sse: false, config: false, timestamp: false }, valid: true },
  { name: "SSE only", state: { sse: true, config: false, timestamp: false }, valid: true },
  { name: "config poll only", state: { sse: false, config: true, timestamp: false }, valid: true },
  {
    name: "timestamp poll only",
    state: { sse: false, config: false, timestamp: true },
    valid: true,
  },
  {
    name: "SSE and config poll",
    state: { sse: true, config: true, timestamp: false },
    valid: false,
  },
  {
    name: "SSE and timestamp poll",
    state: { sse: true, config: false, timestamp: true },
    valid: false,
  },
  {
    name: "config and timestamp polls",
    state: { sse: false, config: true, timestamp: true },
    valid: false,
  },
  { name: "all polling modes", state: { sse: true, config: true, timestamp: true }, valid: false },
];

for (const { name, state, valid } of pollingModeCases) {
  test(`assertSinglePollingMode validates ${name}`, () => {
    const assertionCalls: Array<{ condition: boolean; message: string }> = [];
    const result = assertSinglePollingMode(state, (condition, message) => {
      assertionCalls.push({ condition, message });
    });

    assert.equal(result, valid);
    assert.equal(assertionCalls.length, 1);
    assert.equal(assertionCalls[0].condition, valid);
  });
}

test("startConfigPolling schedules one config refresh interval", async () => {
  const setIntervalCalls: Array<{ callback: () => void; delayMs: number }> = [];
  const createdInterval = { id: "config-poll-interval" } as unknown as ReturnType<
    typeof setInterval
  >;
  let updateCalls = 0;
  const state = {
    configPollingInterval: null as ReturnType<typeof setInterval> | null,
    configInitialLoadPending: false,
  };
  const dependencies: ConfigPollingDependencies = {
    updateConfig: async () => {
      updateCalls += 1;
    },
    logError: () => {},
    scheduleInterval: (callback, delayMs) => {
      setIntervalCalls.push({ callback, delayMs });
      return createdInterval;
    },
  };

  startConfigPolling(state, dependencies);
  startConfigPolling(state, dependencies);

  assert.equal(setIntervalCalls.length, 1);
  assert.equal(setIntervalCalls[0].delayMs, CONFIG_POLL_INTERVAL_MS);
  assert.equal(state.configPollingInterval, createdInterval);
  setIntervalCalls[0].callback();
  await Promise.resolve();
  assert.equal(updateCalls, 1);
});
