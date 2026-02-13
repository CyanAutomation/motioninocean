import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

function extractShowDiagnosticResults(source) {
  const start = source.indexOf("function showDiagnosticResults");
  const end = source.indexOf("\nasync function setDiscoveryApproval", start);
  if (start === -1 || end === -1) {
    throw new Error("showDiagnosticResults() definition not found");
  }
  return source.slice(start, end).trim();
}

function buildDiagnosticResult() {
  return {
    node_id: "node-1",
    diagnostics: {
      registration: { valid: true },
      url_validation: { blocked: false },
      dns_resolution: { resolves: true, resolved_ips: ["10.0.0.2"] },
      network_connectivity: { reachable: true },
      api_endpoint: { status_code: 200, healthy: true },
    },
    guidance: [],
  };
}

test("showDiagnosticResults does not throw when navigator.clipboard is missing", () => {
  const managementJs = fs.readFileSync("pi_camera_in_docker/static/js/management.js", "utf8");
  const showDiagnosticResultsFn = extractShowDiagnosticResults(managementJs);

  const context = {
    alert: () => {},
    globalThis: {},
  };

  vm.runInNewContext(`${showDiagnosticResultsFn};`, context);

  assert.doesNotThrow(() => {
    context.showDiagnosticResults(buildDiagnosticResult());
  });
});

test("showDiagnosticResults catches async clipboard write errors", async () => {
  const managementJs = fs.readFileSync("pi_camera_in_docker/static/js/management.js", "utf8");
  const showDiagnosticResultsFn = extractShowDiagnosticResults(managementJs);

  let writeCalls = 0;
  const context = {
    alert: () => {},
    globalThis: {
      navigator: {
        clipboard: {
          writeText: () => {
            writeCalls += 1;
            return Promise.reject(new Error("clipboard denied"));
          },
        },
      },
    },
  };

  vm.runInNewContext(`${showDiagnosticResultsFn};`, context);

  assert.doesNotThrow(() => {
    context.showDiagnosticResults(buildDiagnosticResult());
  });

  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(writeCalls, 1);
});
