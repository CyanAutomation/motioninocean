import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

function extractRefreshConfigPanel(source) {
  const match = source.match(/function refreshConfigPanel\(\) \{[\s\S]*?\n^}/m);
  if (!match) {
    throw new Error("refreshConfigPanel() definition not found");
  }
  return match[0];
}

test("refreshConfigPanel marks initial load pending and requests config update", async () => {
  const appJs = fs.readFileSync("pi_camera_in_docker/static/js/app.js", "utf8");
  const refreshConfigPanelFn = extractRefreshConfigPanel(appJs);

  let updateCalls = 0;
  const context = {
    state: {
      configInitialLoadPending: false,
    },
    updateConfig: async () => {
      updateCalls += 1;
    },
    console: {
      error: () => {},
    },
  };

  vm.runInNewContext(`${refreshConfigPanelFn};`, context);
  context.refreshConfigPanel();
  await Promise.resolve();

  assert.equal(context.state.configInitialLoadPending, true);
  assert.equal(updateCalls, 1);
});
