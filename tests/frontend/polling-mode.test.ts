import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { assertSinglePollingMode } from "../../frontend/src/polling-mode.ts";
import { asTestDouble } from "./test-doubles.ts";

function extractStartConfigPolling(source: string): string {
  const match = source.match(/function startConfigPolling\(\) \{[\s\S]*?\n^}/m);
  if (!match) {
    throw new Error("startConfigPolling() definition not found");
  }
  return match[0];
}

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

test("startConfigPolling schedules a single 5s config polling interval", () => {
  const appJs = fs.readFileSync("pi_camera_in_docker/static/js/app.js", "utf8");
  const startConfigPollingFn = extractStartConfigPolling(appJs);

  const setIntervalCalls: Array<{
    callback: () => Promise<void>;
    delayMs: number;
  }> = [];
  const createdInterval = { id: "config-poll-interval" };
  const context = {
    state: { configPollingInterval: null as unknown },
    CONFIG_POLL_INTERVAL_MS: 5000,
    updateConfig: () => Promise.resolve(),
    console: { error: () => {} },
    setInterval: (callback: () => Promise<void>, delayMs: number) => {
      setIntervalCalls.push({ callback, delayMs });
      return createdInterval;
    },
  };

  vm.runInNewContext(`${startConfigPollingFn};`, context);

  const evaluatedContext = asTestDouble<typeof context & { startConfigPolling(): void }>(context);
  evaluatedContext.startConfigPolling();
  evaluatedContext.startConfigPolling();
  evaluatedContext.startConfigPolling();

  assert.equal(setIntervalCalls.length, 1);
  assert.equal(setIntervalCalls[0].delayMs, 5000);
  assert.equal(context.state.configPollingInterval, createdInterval);
});
