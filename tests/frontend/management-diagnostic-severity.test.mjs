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

test("diagnostic rows prefer structured status over derived booleans", () => {
  const managementJs = fs.readFileSync("pi_camera_in_docker/static/js/management.js", "utf8");
  const rowsFn = slice(
    managementJs,
    "function getDiagnosticCheckRows",
    "function getDiagnosticSummaryState",
  );

  const context = {};
  vm.runInNewContext(`${rowsFn}`, context);

  const rows = context.getDiagnosticCheckRows({
    registration: { valid: true, status: "warn", code: "REG_WARN" },
    url_validation: { blocked: false, status: "pass" },
    dns_resolution: { resolves: true, status: "pass", resolved_ips: ["203.0.113.1"] },
    network_connectivity: {
      reachable: true,
      status: "warn",
      category: "timeout",
      code: "NETWORK_WARN",
    },
    api_endpoint: {
      accessible: true,
      healthy: true,
      status_code: 200,
      status: "fail",
      code: "API_FAIL",
    },
  });

  assert.equal(rows[0].state, "warn");
  assert.match(rows[0].meta, /REG_WARN/);
  assert.equal(rows[3].state, "warn");
  assert.match(rows[3].meta, /NETWORK_WARN/);
  assert.equal(rows[4].state, "fail");
  assert.match(rows[4].meta, /API_FAIL/);
});

test("diagnostic summary/banner map connectivity categories to concise remediation", () => {
  const managementJs = fs.readFileSync("pi_camera_in_docker/static/js/management.js", "utf8");
  const summaryFns = slice(
    managementJs,
    "function getDiagnosticSummaryState",
    "function renderDiagnosticRecommendations",
  );

  const context = {};
  vm.runInNewContext(`${summaryFns}`, context);

  const summary = context.getDiagnosticSummaryState([
    { key: "Registration", state: "pass" },
    { key: "URL validation", state: "pass" },
    { key: "DNS resolution", state: "pass" },
    { key: "Network connectivity", state: "fail" },
    { key: "API endpoint", state: "pass" },
  ]);
  assert.equal(summary.label, "Action required");

  const banner = context.getDiagnosticSummaryBanner(
    summary,
    [
      { key: "Registration", state: "pass" },
      { key: "URL validation", state: "pass" },
      { key: "DNS resolution", state: "pass" },
      { key: "Network connectivity", state: "fail" },
      { key: "API endpoint", state: "pass" },
    ],
    {
      network_connectivity: { category: "timeout", code: "NETWORK_CONNECTIVITY_ERROR" },
      url_validation: {},
      registration: {},
    },
  );

  assert.match(banner.interpretation, /timed out/i);
  assert.equal(banner.cta, "Retry in 30s");
});
