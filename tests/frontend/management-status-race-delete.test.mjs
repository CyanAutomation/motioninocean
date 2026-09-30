import test from "node:test";
import assert from "node:assert/strict";
import { createStatusRefresher } from "../../frontend/src/management-status.ts";

test("refreshStatuses discards stale in-flight poll result when webcam dataset changes", async () => {
  const pendingByNodeId = new Map();
  let nodes = [{ id: "node-a" }, { id: "node-b" }];
  let datasetVersion = 1;
  let statuses = new Map([["node-a", { status: "ok", stream_available: true }]]);
  const history = new Map();
  let renderCount = 0;
  const refreshStatuses = createStatusRefresher({
    getNodes: () => nodes,
    getDatasetVersion: () => datasetVersion,
    getStatusHistory: () => history,
    fetchStatusesForNodes: async (nodeIds) => {
      const entries = await Promise.all(
        Array.from(
          nodeIds,
          (nodeId) =>
            new Promise((resolve) => {
              pendingByNodeId.set(nodeId, () =>
                resolve([nodeId, { status: "ok", stream_available: true }]),
              );
            }),
        ),
      );
      return new Map(entries);
    },
    setStatuses: (next) => {
      statuses = next;
    },
    showUnauthorizedFeedback: () => {},
    renderRows: () => {
      renderCount += 1;
    },
    renderDiscoveredPanel: () => {},
    renderOverviewPanel: () => {},
    appendActivityFeed: () => {},
  });

  const refreshPromise = refreshStatuses();
  await new Promise((resolve) => setImmediate(resolve));

  nodes = [{ id: "node-a" }];
  datasetVersion += 1;

  pendingByNodeId.get("node-a")?.();
  pendingByNodeId.get("node-b")?.();
  await refreshPromise;

  assert.deepEqual(Array.from(statuses.keys()), ["node-a"]);
  assert.equal(statuses.get("node-a")?.status, "ok");
  assert.equal(statuses.has("node-b"), false);
  assert.equal(renderCount, 0);
});
