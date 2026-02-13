import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

function slice(source, startToken, endToken) {
  const start = source.indexOf(startToken);
  const end = source.indexOf(endToken, start);
  if (start === -1 || end === -1) {
    throw new Error(`Unable to slice from ${startToken} to ${endToken}`);
  }
  return source.slice(start, end).trim();
}

test("management status UI maps NODE_API_MISMATCH to failure subtype with actionable reason", () => {
  const managementJs = fs.readFileSync("pi_camera_in_docker/static/js/management.js", "utf8");
  const statusClassFn = slice(managementJs, "function statusClass", "const STATUS_SUBTYPE_CONFIG");
  const subtypeConfig = slice(
    managementJs,
    "const STATUS_SUBTYPE_CONFIG",
    "function normalizeNodeStatusError",
  );
  const reasonFn = slice(
    managementJs,
    "function getStatusReason",
    "function normalizeNodeStatusForUi",
  );
  const normalizeFn = slice(
    managementJs,
    "function normalizeNodeStatusForUi",
    "function renderRows",
  );

  const context = {};
  vm.runInNewContext(`${statusClassFn}\n${subtypeConfig}\n${reasonFn}\n${normalizeFn}`, context);

  const status = {
    status: "error",
    error_code: "NODE_API_MISMATCH",
    error_message: "node foo status probe endpoint was not found",
    error_details: {
      expected_endpoint: "/api/status",
      received_status_code: 404,
    },
  };

  const normalized = context.normalizeNodeStatusForUi(status);
  assert.equal(normalized.subtype, "no_response");
  assert.equal(normalized.label, "No response");
  assert.equal(normalized.statusClass, "ui-status-pill--error");
  assert.match(normalized.reasonText, /Node API does not match expected management endpoints\./);
  assert.match(normalized.reasonText, /exposes \/api\/status\./);
});
