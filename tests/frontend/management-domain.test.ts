import test from "node:test";
import assert from "node:assert/strict";

import {
  formatAggregationDetails,
  formatDateTime,
  getDiscoveryInfo,
  isFailureStatus,
  normalizeWebcamStatusForUi,
  normalizeWebcamStatusError,
  statusClass,
} from "../../frontend/src/management-domain.ts";

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

  assert.deepEqual(
    normalizeWebcamStatusError({
      code: "SSRF_BLOCKED",
      message: "blocked",
      details: { host: "127.0.0.1" },
    }),
    {
      status: "error",
      stream_available: false,
      error_code: "SSRF_BLOCKED",
      error_message: "blocked",
      error_details: { host: "127.0.0.1" },
    },
  );
});

test("discovery metadata defaults manual nodes to approved and uses last seen as first seen", () => {
  assert.deepEqual(getDiscoveryInfo({ id: "manual", last_seen: "2026-01-02T03:04:05Z" }), {
    source: "manual",
    firstSeen: "2026-01-02T03:04:05Z",
    lastAnnounceAt: null,
    approved: true,
  });
  assert.deepEqual(
    getDiscoveryInfo({
      id: "discovered",
      discovery: { source: "discovered", approved: false, first_seen: "first" },
    }),
    { source: "discovered", firstSeen: "first", lastAnnounceAt: null, approved: false },
  );
});

test("status presentation distinguishes healthy, incomplete, and unauthorized responses", () => {
  assert.deepEqual(normalizeWebcamStatusForUi({ status: "ok", ready: true }), {
    subtype: "healthy",
    label: "Healthy",
    helpText: "Node is ready and healthy.",
    statusClass: "ui-status-pill--success",
    reasonText: "Ready and responding.",
  });
  assert.equal(
    normalizeWebcamStatusForUi({ status: "ready", ready: false }).subtype,
    "partial_probe",
  );
  const unauthorized = normalizeWebcamStatusForUi({
    status: "error",
    error_code: "WEBCAM_UNAUTHORIZED",
  });
  assert.equal(unauthorized.label, "Unauthorized");
  assert.match(unauthorized.reasonText, /Token\/auth mismatch/);
});

test("status history details and date formatting keep stable fallbacks", () => {
  assert.equal(formatDateTime(null), "—");
  assert.equal(formatDateTime("not-a-date"), "not-a-date");
  assert.match(formatDateTime("2026-01-02T03:04:05Z"), /2026/);

  const details = formatAggregationDetails({
    last_success_at: "not-a-date",
    first_failure_at: "2026-01-03T03:04:05Z",
    consecutive_failures: 2,
  });
  assert.match(details, /Last success: not-a-date/);
  assert.match(details, /First failure:/);
  assert.match(details, /Consecutive failures: 2/);
});
