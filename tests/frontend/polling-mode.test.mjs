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
