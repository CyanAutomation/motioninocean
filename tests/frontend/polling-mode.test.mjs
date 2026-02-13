import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

function extractAssertSinglePollingMode(source) {
  const match = source.match(/function assertSinglePollingMode\(\) \{[\s\S]*?\n^}/m);
  if (!match) {
    throw new Error("assertSinglePollingMode() definition not found");
  }
  return match[0];
}

function extractStartConfigPolling(source) {
  const match = source.match(/function startConfigPolling\(\) \{[\s\S]*?\n^}/m);
  if (!match) {
    throw new Error("startConfigPolling() definition not found");
  }
  return match[0];
}

test("assertSinglePollingMode only allows one polling mode at a time", () => {
  const appJs = fs.readFileSync("pi_camera_in_docker/static/js/app.js", "utf8");
  const assertSinglePollingModeFn = extractAssertSinglePollingMode(appJs);

  const consoleAssertCalls = [];
  const context = {
    state: {
      updateInterval: null,
      configPollingInterval: null,
      configTimestampInterval: null,
    },
    console: {
      assert: (condition, message) => {
        consoleAssertCalls.push({ condition, message });
      },
    },
  };

  vm.runInNewContext(`${assertSinglePollingModeFn};`, context);

  context.assertSinglePollingMode();
  context.state.updateInterval = 1;
  context.assertSinglePollingMode();
  context.state.updateInterval = null;
  context.state.configPollingInterval = 1;
  context.assertSinglePollingMode();
  context.state.configPollingInterval = null;
  context.state.configTimestampInterval = 1;
  context.assertSinglePollingMode();

  context.state.updateInterval = 1;
  context.state.configPollingInterval = 1;
  context.assertSinglePollingMode();

  const lastCall = consoleAssertCalls.at(-1);
  assert.equal(lastCall.condition, false);
  assert.equal(
    lastCall.message,
    "Invalid polling state: stats and config polling are both active.",
  );
});

test("startConfigPolling schedules a single 5s config polling interval", () => {
  const appJs = fs.readFileSync("pi_camera_in_docker/static/js/app.js", "utf8");
  const startConfigPollingFn = extractStartConfigPolling(appJs);

  const setIntervalCalls = [];
  const createdInterval = { id: "config-poll-interval" };
  const context = {
    state: { configPollingInterval: null },
    CONFIG_POLL_INTERVAL_MS: 5000,
    updateConfig: () => Promise.resolve(),
    console: { error: () => {} },
    setInterval: (callback, delayMs) => {
      setIntervalCalls.push({ callback, delayMs });
      return createdInterval;
    },
  };

  vm.runInNewContext(`${startConfigPollingFn};`, context);

  context.startConfigPolling();
  context.startConfigPolling();
  context.startConfigPolling();

  assert.equal(setIntervalCalls.length, 1);
  assert.equal(setIntervalCalls[0].delayMs, 5000);
  assert.equal(context.state.configPollingInterval, createdInterval);
});
