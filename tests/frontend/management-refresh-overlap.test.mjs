import test from "node:test";
import assert from "node:assert/strict";
import { createStatusRefresher } from "../../pi_camera_in_docker/static/js/management-status.js";

test("refreshStatuses schedules a second pass for overlapping timer+manual calls without duplicate feedback", async () => {
  const feedbackCalls = [];
  let fetchCount = 0;
  let resolveFirstFetch;
  const nodes = [{ id: "node-a" }];
  let statuses = new Map();
  const refreshStatuses = createStatusRefresher({
    getNodes: () => nodes,
    getDatasetVersion: () => 1,
    getStatusHistory: () => new Map(),
    fetchStatusesForNodes: async (nodeIds, allowManualFeedback, onUnauthorized) => {
      fetchCount += 1;
      if (allowManualFeedback) onUnauthorized();
      if (fetchCount === 1) {
        return new Promise((resolve) => {
          resolveFirstFetch = () =>
            resolve(new Map(Array.from(nodeIds, (id) => [id, { status: "error" }])));
        });
      }
      return new Map(Array.from(nodeIds, (id) => [id, { status: "error" }]));
    },
    setStatuses: (next) => {
      statuses = next;
    },
    showUnauthorizedFeedback: () => feedbackCalls.push(["hint", true]),
    renderRows: () => {},
    renderDiscoveredPanel: () => {},
    renderOverviewPanel: () => {},
    appendActivityFeed: () => {},
  });

  const intervalRun = refreshStatuses({ fromInterval: true });
  await new Promise((resolve) => setImmediate(resolve));

  await refreshStatuses();
  resolveFirstFetch();
  await intervalRun;

  assert.equal(fetchCount, 2);
  assert.equal(feedbackCalls.length, 1);
  assert.deepEqual(feedbackCalls[0], ["hint", true]);
  assert.equal(statuses.get("node-a").status, "error");
});

test("refreshStatuses preserves manual feedback for the first manual unauthorized cycle", async () => {
  const feedbackCalls = [];
  const refreshStatuses = createStatusRefresher({
    getNodes: () => [{ id: "node-a" }],
    getDatasetVersion: () => 0,
    getStatusHistory: () => new Map(),
    fetchStatusesForNodes: async (nodeIds, allowManualFeedback, onUnauthorized) => {
      if (allowManualFeedback) onUnauthorized();
      return new Map(Array.from(nodeIds, (id) => [id, { status: "error" }]));
    },
    setStatuses: () => {},
    showUnauthorizedFeedback: () => feedbackCalls.push(["hint", true]),
    renderRows: () => {},
    renderDiscoveredPanel: () => {},
    renderOverviewPanel: () => {},
    appendActivityFeed: () => {},
  });

  await refreshStatuses();

  assert.equal(feedbackCalls.length, 1);
  assert.deepEqual(feedbackCalls[0], ["hint", true]);
});
