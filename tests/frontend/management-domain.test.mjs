import test from "node:test";
import assert from "node:assert/strict";

import {
  isFailureStatus,
  normalizeWebcamStatusError,
  statusClass,
} from "../../pi_camera_in_docker/static/js/management-domain.js";

test("management status helpers classify healthy, failed, and unknown states", () => {
  assert.equal(statusClass("ready"), "ui-status-pill--success");
  assert.equal(statusClass("unhealthy"), "ui-status-pill--error");
  assert.equal(statusClass("pending"), "ui-status-pill--neutral");
  assert.equal(isFailureStatus({ status: "unauthorized" }), true);
  assert.equal(isFailureStatus({ status: "ok" }), false);
  assert.equal(isFailureStatus({ error_code: "NETWORK_UNREACHABLE" }), true);
});

test("management status error normalization supplies stable fallback fields", () => {
  assert.deepEqual(normalizeWebcamStatusError(), {
    status: "error",
    stream_available: false,
    error_code: "UNKNOWN_ERROR",
    error_message: "Node status request failed.",
    error_details: null,
  });

  assert.deepEqual(normalizeWebcamStatusError({
    code: "SSRF_BLOCKED",
    message: "blocked",
    details: { host: "127.0.0.1" },
  }), {
    status: "error",
    stream_available: false,
    error_code: "SSRF_BLOCKED",
    error_message: "blocked",
    error_details: { host: "127.0.0.1" },
  });
});
