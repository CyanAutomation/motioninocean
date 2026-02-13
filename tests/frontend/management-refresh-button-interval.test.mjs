import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

function extractInit(source) {
  const start = source.indexOf("async function init()");
  const end = source.indexOf("\n\ninit().catch", start);
  if (start === -1 || end === -1) {
    throw new Error("init() definition not found");
  }
  return source.slice(start, end).trim();
}

test("refresh button always restarts status interval even when refresh fails", async () => {
  const managementJs = fs.readFileSync("pi_camera_in_docker/static/js/management.js", "utf8");
  const initFn = extractInit(managementJs);

  let refreshClickHandler;
  let fetchNodesCalls = 0;
  let startIntervalCalls = 0;
  let stopIntervalCalls = 0;
  let refreshStatusesCalls = 0;
  const feedbackCalls = [];

  const context = {
    nodeForm: { addEventListener: () => {} },
    cancelEditBtn: { addEventListener: () => {}, classList: { add: () => {} } },
    refreshBtn: {
      addEventListener: (event, handler) => {
        if (event === "click") {
          refreshClickHandler = handler;
        }
      },
    },
    tableBody: { addEventListener: () => {} },
    resetForm: () => {},
    submitNodeForm: () => {},
    showFeedback: (...args) => feedbackCalls.push(args),
    stopStatusRefreshInterval: () => {
      stopIntervalCalls += 1;
    },
    startStatusRefreshInterval: () => {
      startIntervalCalls += 1;
    },
    fetchNodes: async () => {
      fetchNodesCalls += 1;
      if (fetchNodesCalls === 2) {
        throw new Error("offline");
      }
    },
    refreshStatuses: async () => {
      refreshStatusesCalls += 1;
    },
    onTableClick: () => {},
  };

  vm.runInNewContext(`${initFn};`, context);

  await context.init();
  assert.equal(typeof refreshClickHandler, "function");

  await assert.rejects(() => refreshClickHandler(), /offline/);

  assert.equal(stopIntervalCalls, 1);
  assert.equal(startIntervalCalls, 2);
  assert.equal(refreshStatusesCalls, 1);
  assert.equal(
    feedbackCalls.some(([message]) => message === "Node list refreshed."),
    false,
  );
});
