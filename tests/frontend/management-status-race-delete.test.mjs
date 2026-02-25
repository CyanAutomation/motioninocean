import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

function extractRefreshStatuses(source) {
  const start = source.indexOf("async function refreshStatuses");
  const end = source.indexOf("\nfunction resetForm", start);
  if (start === -1 || end === -1) {
    throw new Error("refreshStatuses() definition not found");
  }
  return source.slice(start, end).trim();
}

test("refreshStatuses discards stale in-flight poll result when webcam dataset changes", async () => {
  const managementJs = fs.readFileSync("pi_camera_in_docker/static/js/management.js", "utf8");
  const refreshStatusesFn = extractRefreshStatuses(managementJs);

  const pendingByNodeId = new Map();
  const context = {
    webcams: [{ id: "node-a" }, { id: "node-b" }],
    webcamDatasetVersion: 1,
    webcamStatusMap: new Map([["node-a", { status: "ok", stream_available: true }]]),
    previousStatusByNode: new Map(),
    statusRefreshInFlight: false,
    statusRefreshPending: false,
    statusRefreshPendingManual: false,
    statusRefreshToken: 0,
    API_AUTH_HINT: "hint",
    renderRows: () => {},
    renderDiscoveredPanel: () => {},
    renderOverviewPanel: () => {},
    appendActivityFeed: () => {},
    showFeedback: () => {},
    normalizeWebcamStatusError: (error = {}) => ({
      status: "error",
      stream_available: false,
      error_code: error.code || "UNKNOWN_ERROR",
      error_message: error.message || "Webcam status request failed.",
      error_details: error.details || null,
    }),
    enrichStatusWithAggregation: (_webcamId, status) => status,
    fetch: (path) => {
      const match = path.match(/\/api\/v1\/webcams\/([^/]+)\/status$/);
      const nodeId = decodeURIComponent(match?.[1] || "");
      return new Promise((resolve) => {
        pendingByNodeId.set(nodeId, () =>
          resolve({
            ok: true,
            status: 200,
            json: async () => ({ status: "ok", stream_available: true }),
          }),
        );
      });
    },
  };

  vm.runInNewContext(`${refreshStatusesFn};`, context);
  vm.runInNewContext(
    `managementFetch = async (path) => fetch(path);`,
    context,
  );

  const refreshPromise = context.refreshStatuses();
  await new Promise((resolve) => setImmediate(resolve));

  context.webcams = [{ id: "node-a" }];
  context.webcamDatasetVersion += 1;

  pendingByNodeId.get("node-a")?.();
  pendingByNodeId.get("node-b")?.();
  await refreshPromise;

  assert.deepEqual(Array.from(context.webcamStatusMap.keys()), ["node-a"]);
  assert.equal(context.webcamStatusMap.get("node-a")?.status, "ok");
  assert.equal(context.webcamStatusMap.has("node-b"), false);
});
