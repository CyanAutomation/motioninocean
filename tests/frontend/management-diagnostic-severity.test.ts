import test from "node:test";
import assert from "node:assert/strict";
import {
  getDiagnosticCheckRows,
  getDiagnosticSummaryBanner,
  getDiagnosticSummaryState,
} from "../../frontend/src/management-diagnostics.ts";

const row = (key: string, state: "pass" | "warn" | "fail") => ({
  key,
  state,
  detail: "",
  meta: "",
});

test("diagnostic rows prefer structured status over derived booleans", () => {
  const rows = getDiagnosticCheckRows({
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
  const summary = getDiagnosticSummaryState([
    row("Registration", "pass"),
    row("URL validation", "pass"),
    row("DNS resolution", "pass"),
    row("Network connectivity", "fail"),
    row("API endpoint", "pass"),
  ]);
  assert.equal(summary.label, "Action required");

  const banner = getDiagnosticSummaryBanner(
    summary,
    [
      row("Registration", "pass"),
      row("URL validation", "pass"),
      row("DNS resolution", "pass"),
      row("Network connectivity", "fail"),
      row("API endpoint", "pass"),
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

test("diagnostic summary distinguishes transient API warnings from actionable warnings", () => {
  const transientSummary = getDiagnosticSummaryState([row("API endpoint", "warn")]);
  const actionableSummary = getDiagnosticSummaryState([row("Network connectivity", "warn")]);

  assert.equal(transientSummary.label, "Warning");
  assert.equal(actionableSummary.label, "Action recommended");
});
