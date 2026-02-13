import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

function extractDiagnosticHelpers(source) {
  const start = source.indexOf("function getDiagnosticCheckRows");
  const end = source.indexOf("\nasync function setDiscoveryApproval", start);
  if (start === -1 || end === -1) {
    throw new Error("diagnostic helpers definition not found");
  }
  return source.slice(start, end).trim();
}

function extractCopyHandlerBody(source) {
  const marker = 'copyDiagnosticReportBtn.addEventListener("click", async () => {';
  const start = source.indexOf(marker);
  if (start === -1) {
    throw new Error("copy handler definition not found");
  }

  let i = start + marker.length;
  let depth = 1;
  while (i < source.length && depth > 0) {
    const char = source[i];
    if (char === "{") depth += 1;
    if (char === "}") depth -= 1;
    i += 1;
  }

  if (depth !== 0) {
    throw new Error("copy handler braces did not balance");
  }

  return source.slice(start + marker.length, i - 1).trim();
}

function buildUiContext() {
  const panelFocus = { called: 0 };
  return {
    escapeHtml: (value) => String(value),
    latestDiagnosticResult: null,
    diagnosticNodeId: { textContent: "" },
    diagnosticContext: { textContent: "" },
    diagnosticSummaryBadge: { className: "", textContent: "" },
    diagnosticOverallStatePill: { className: "", textContent: "" },
    diagnosticSummaryInterpretation: { textContent: "" },
    diagnosticSummaryCta: { textContent: "" },
    diagnosticChecksGrid: { innerHTML: "" },
    diagnosticRecommendations: { innerHTML: "" },
    copyDiagnosticReportBtn: { disabled: true },
    diagnosticPanel: { focus: () => (panelFocus.called += 1) },
    panelFocus,
    globalThis: {},
  };
}

function evaluateHelpers() {
  const managementJs = fs.readFileSync("pi_camera_in_docker/static/js/management.js", "utf8");
  const helperSource = extractDiagnosticHelpers(managementJs);
  const context = buildUiContext();
  vm.runInNewContext(`${helperSource};`, context);
  return context;
}

function runCopyHandler(context, body) {
  const copyFn = vm.runInNewContext(`(async () => {${body}})`, context);
  return copyFn();
}

test("showDiagnosticResults populates panel, rows, recommendations, and focuses panel", () => {
  const context = evaluateHelpers();

  context.showDiagnosticResults({
    node_id: "node-1",
    diagnostics: {
      registration: { valid: true, status: "pass" },
      url_validation: { blocked: false, status: "pass" },
      dns_resolution: { resolves: true, status: "warn", resolved_ips: ["203.0.113.10"] },
      network_connectivity: { reachable: false, status: "fail", code: "NETWORK_CONNECTIVITY_ERROR" },
      api_endpoint: { accessible: true, healthy: true, status: "pass", status_code: 200 },
    },
    recommendations: [
      { message: "Confirm DNS zone", status: "warn", code: "DNS_WARN" },
      { message: "Restart node service", status: "fail", code: "NETWORK_CONNECTIVITY_ERROR" },
      { message: "Baseline check ok", status: "pass" },
    ],
    guidance: [],
  });

  assert.equal(context.diagnosticNodeId.textContent, "node-1");
  assert.match(context.diagnosticContext.textContent, /Generated at/);
  assert.match(context.diagnosticChecksGrid.innerHTML, /Registration/);
  assert.match(context.diagnosticChecksGrid.innerHTML, /diagnostic-pill--pass/);
  assert.match(context.diagnosticChecksGrid.innerHTML, /diagnostic-pill--warn/);
  assert.match(context.diagnosticChecksGrid.innerHTML, /diagnostic-pill--fail/);
  assert.match(context.diagnosticRecommendations.innerHTML, /<h4>Recommendations<\/h4>/);
  assert.match(context.diagnosticRecommendations.innerHTML, /<ul>/);
  assert.match(context.diagnosticRecommendations.innerHTML, /<li><span class="diagnostic-pill diagnostic-pill--warn">\[WARN\]<\/span>/);
  assert.match(context.diagnosticRecommendations.innerHTML, /diagnostic-pill--fail">\[FAIL\]/);
  assert.match(context.diagnosticRecommendations.innerHTML, /diagnostic-pill--pass">\[PASS\]/);
  assert.equal(context.copyDiagnosticReportBtn.disabled, false);
  assert.equal(context.panelFocus.called, 1);
});

test("edge state: node not found/registration invalid marks registration as fail", () => {
  const context = evaluateHelpers();
  const rows = context.getDiagnosticCheckRows({
    registration: { valid: false, status: "fail", error: "Node not found", code: "NODE_NOT_FOUND" },
  });

  assert.equal(rows[0].state, "fail");
  assert.match(rows[0].detail, /Node not found/);
  assert.match(rows[0].meta, /NODE_NOT_FOUND/);
});

test("edge state: DNS failure renders fail state in diagnostics panel", () => {
  const context = evaluateHelpers();
  context.showDiagnosticResults({
    node_id: "dns-node",
    diagnostics: {
      registration: { valid: true, status: "pass" },
      url_validation: { blocked: false, status: "pass" },
      dns_resolution: { resolves: false, status: "fail", error: "Hostname could not be resolved" },
      network_connectivity: { reachable: false, status: "fail" },
      api_endpoint: { accessible: false, status: "fail" },
    },
    guidance: [],
  });

  assert.match(context.diagnosticChecksGrid.innerHTML, /DNS resolution/);
  assert.match(context.diagnosticChecksGrid.innerHTML, /Hostname could not be resolved/);
  assert.match(context.diagnosticChecksGrid.innerHTML, /diagnostic-pill--fail">FAIL/);
});

test("edge state: reachable + HTTP 503 uses warning summary and initialization messaging", () => {
  const context = evaluateHelpers();
  context.showDiagnosticResults({
    node_id: "warmup-node",
    diagnostics: {
      registration: { valid: true, status: "pass" },
      url_validation: { blocked: false, status: "pass" },
      dns_resolution: { resolves: true, status: "pass" },
      network_connectivity: { reachable: true, status: "pass" },
      api_endpoint: { accessible: true, healthy: false, status: "warn", status_code: 503, code: "API_STATUS_503" },
    },
    guidance: [],
  });

  assert.equal(context.diagnosticSummaryBadge.textContent, "Warning");
  assert.match(context.diagnosticChecksGrid.innerHTML, /HTTP 503/);
  assert.match(context.diagnosticChecksGrid.innerHTML, /still be initializing/);
  assert.match(context.diagnosticSummaryInterpretation.textContent, /warming up/i);
});

test("edge state: blocked URL validation renders fail and SSRF detail", () => {
  const context = evaluateHelpers();
  context.showDiagnosticResults({
    node_id: "blocked-node",
    diagnostics: {
      registration: { valid: true, status: "pass" },
      url_validation: { blocked: true, status: "fail", blocked_reason: "Blocked by SSRF policy", code: "SSRF_BLOCKED" },
      dns_resolution: { resolves: false, status: "fail" },
      network_connectivity: { reachable: false, status: "fail" },
      api_endpoint: { accessible: false, status: "fail" },
    },
    guidance: [],
  });

  assert.match(context.diagnosticChecksGrid.innerHTML, /URL validation/);
  assert.match(context.diagnosticChecksGrid.innerHTML, /Blocked by SSRF policy/);
  assert.match(context.diagnosticChecksGrid.innerHTML, /Code: SSRF_BLOCKED/);
  assert.match(context.diagnosticSummaryInterpretation.textContent, /SSRF protection blocked/i);
});

test("accessibility markup keeps heading/list semantics and aria-live panel", () => {
  const template = fs.readFileSync("pi_camera_in_docker/templates/management.html", "utf8");

  assert.match(template, /<section[\s\S]*id="diagnostic-panel"[\s\S]*aria-live="polite"/);
  assert.match(template, /<h3>Diagnostic report<\/h3>/);
  assert.match(template, /<div class="diagnostic-recommendations" id="diagnostic-recommendations">[\s\S]*<h4>Recommendations<\/h4>[\s\S]*<ul>/);
});

test("clipboard resilience: explicit Copy action reports unavailable clipboard", async () => {
  const managementJs = fs.readFileSync("pi_camera_in_docker/static/js/management.js", "utf8");
  const copyHandlerBody = extractCopyHandlerBody(managementJs);
  const context = {
    latestDiagnosticResult: {
      node_id: "node-1",
      diagnostics: {},
      guidance: [],
      recommendations: [],
    },
    buildDiagnosticTextReport: () => "report",
    showFeedback: (message, isError = false) => {
      context.lastFeedback = { message, isError };
    },
    globalThis: {},
  };

  await runCopyHandler(context, copyHandlerBody);

  assert.deepEqual(context.lastFeedback, {
    message: "Clipboard not available in this browser.",
    isError: true,
  });
});

test("clipboard resilience: explicit Copy action handles clipboard rejection", async () => {
  const managementJs = fs.readFileSync("pi_camera_in_docker/static/js/management.js", "utf8");
  const copyHandlerBody = extractCopyHandlerBody(managementJs);
  let writeCalls = 0;
  const context = {
    latestDiagnosticResult: {
      node_id: "node-1",
      diagnostics: {},
      guidance: [],
      recommendations: [],
    },
    buildDiagnosticTextReport: () => "report",
    showFeedback: (message, isError = false) => {
      context.lastFeedback = { message, isError };
    },
    globalThis: {
      navigator: {
        clipboard: {
          writeText: async () => {
            writeCalls += 1;
            throw new Error("denied");
          },
        },
      },
    },
  };

  await runCopyHandler(context, copyHandlerBody);

  assert.equal(writeCalls, 1);
  assert.deepEqual(context.lastFeedback, {
    message: "Could not copy report to clipboard.",
    isError: true,
  });
});
