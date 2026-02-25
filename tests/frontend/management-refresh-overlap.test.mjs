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

test("refreshStatuses schedules a second pass for overlapping timer+manual calls without duplicate feedback", async () => {
  const managementJs = fs.readFileSync("pi_camera_in_docker/static/js/management.js", "utf8");
  const refreshStatusesFn = extractRefreshStatuses(managementJs);

  const feedbackCalls = [];
  let fetchCount = 0;
  let resolveFirstFetch;

  const unauthorizedResponse = {
    ok: false,
    status: 401,
    json: async () => ({ error: { code: "NODE_UNAUTHORIZED" } }),
  };

  const context = {
    webcams: [{ id: "node-a" }],
    webcamStatusMap: new Map(),
    statusRefreshInFlight: false,
    statusRefreshPending: false,
    statusRefreshPendingManual: false,
    statusRefreshToken: 0,
    webcamDatasetVersion: 1,
    API_AUTH_HINT: "hint",
    renderRows: () => {},
    showFeedback: (...args) => feedbackCalls.push(args),
    normalizeWebcamStatusError: (error = {}) => ({
      status: "error",
      stream_available: false,
      error_code: error.code || "UNKNOWN_ERROR",
      error_message: error.message || "Webcam status request failed.",
      error_details: error.details || null,
    }),
    enrichStatusWithAggregation: (_webcamId, status) => status,
    fetch: () => {
      fetchCount += 1;
      if (fetchCount === 1) {
        return new Promise((resolve) => {
          resolveFirstFetch = () => resolve(unauthorizedResponse);
        });
      }
      return Promise.resolve(unauthorizedResponse);
    },
  };

  vm.runInNewContext(`${refreshStatusesFn};`, context);
  vm.runInNewContext(
    `managementFetch = async (path) => {
      const response = await fetch(path);
      if (response.status === 401) {
        const unauthorizedError = new Error(API_AUTH_HINT);
        unauthorizedError.isUnauthorized = true;
        unauthorizedError.response = response;
        throw unauthorizedError;
      }
      return response;
    };`,
    context,
  );

  const intervalRun = context.refreshStatuses({ fromInterval: true });
  await new Promise((resolve) => setImmediate(resolve));

  await context.refreshStatuses();
  resolveFirstFetch();
  await intervalRun;

  assert.equal(fetchCount, 2);
  assert.equal(feedbackCalls.length, 1);
  assert.deepEqual(feedbackCalls[0], ["hint", true]);
});

test("refreshStatuses preserves manual feedback for the first manual unauthorized cycle", async () => {
  const managementJs = fs.readFileSync("pi_camera_in_docker/static/js/management.js", "utf8");
  const refreshStatusesFn = extractRefreshStatuses(managementJs);

  const feedbackCalls = [];

  const unauthorizedResponse = {
    ok: false,
    status: 401,
    json: async () => ({ error: { code: "NODE_UNAUTHORIZED" } }),
  };

  const context = {
    webcams: [{ id: "node-a" }],
    webcamStatusMap: new Map(),
    statusRefreshInFlight: false,
    statusRefreshPending: false,
    statusRefreshPendingManual: false,
    statusRefreshToken: 0,
    webcamDatasetVersion: 0,
    API_AUTH_HINT: "hint",
    renderRows: () => {},
    showFeedback: (...args) => feedbackCalls.push(args),
    normalizeWebcamStatusError: (error = {}) => ({
      status: "error",
      stream_available: false,
      error_code: error.code || "UNKNOWN_ERROR",
      error_message: error.message || "Webcam status request failed.",
      error_details: error.details || null,
    }),
    enrichStatusWithAggregation: (_webcamId, status) => status,
    fetch: () => Promise.resolve(unauthorizedResponse),
  };

  vm.runInNewContext(`${refreshStatusesFn};`, context);
  vm.runInNewContext(
    `managementFetch = async (path) => {
      const response = await fetch(path);
      if (response.status === 401) {
        const unauthorizedError = new Error(API_AUTH_HINT);
        unauthorizedError.isUnauthorized = true;
        unauthorizedError.response = response;
        throw unauthorizedError;
      }
      return response;
    };`,
    context,
  );

  await context.refreshStatuses();

  assert.equal(feedbackCalls.length, 1);
  assert.deepEqual(feedbackCalls[0], ["hint", true]);
});
