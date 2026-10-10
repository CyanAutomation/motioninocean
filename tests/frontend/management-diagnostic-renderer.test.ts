import test from "node:test";
import assert from "node:assert/strict";
import {
  renderDiagnosticResults,
  type DiagnosticRendererDependencies,
} from "../../frontend/src/management-diagnostic-renderer.ts";

function createDependencies() {
  const elements = {
    diagnosticWebcamId: { textContent: "" },
    diagnosticContext: { textContent: "" },
    diagnosticSummaryBadge: { className: "", textContent: "" },
    diagnosticOverallStatePill: { className: "", textContent: "" } as {
      className: string;
      textContent: string;
    } | null,
    diagnosticSummaryInterpretation: { textContent: "" } as { textContent: string } | null,
    diagnosticSummaryCta: { textContent: "" } as { textContent: string } | null,
    diagnosticChecksGrid: { innerHTML: "" },
    diagnosticRecommendations: { innerHTML: "" },
    copyDiagnosticReportBtn: { disabled: true },
    diagnosticPanel: {
      focused: false,
      focus() {
        this.focused = true;
      },
    },
  };
  const state: {
    expanded: boolean;
    recommendations: { guidance: unknown[]; recommendations: unknown[] } | null;
  } = { expanded: false, recommendations: null };
  const dependencies: DiagnosticRendererDependencies = {
    ...elements,
    escapeHtml: (value: unknown) => String(value).replaceAll("<", "&lt;").replaceAll(">", "&gt;"),
    renderRecommendations: (guidance, recommendations) => {
      state.recommendations = { guidance, recommendations };
    },
    setPanelExpanded: (expanded) => {
      state.expanded = expanded;
    },
    isPanelContentVisible: () => state.expanded,
    now: () => new Date("2026-09-30T12:00:00.000Z"),
  };
  return {
    elements,
    state,
    dependencies,
  };
}

test("renderDiagnosticResults fills summary, escaped checks, recommendations, and focus state", () => {
  const { dependencies, elements, state } = createDependencies();
  renderDiagnosticResults(
    {
      node_id: "<node>",
      diagnostics: {
        registration: { valid: false, status: "fail", error: "<invalid>" },
        url_validation: { blocked: false, status: "pass" },
        dns_resolution: { resolves: true, status: "pass", resolved_ips: ["203.0.113.4"] },
        network_connectivity: { reachable: true, status: "pass" },
        api_endpoint: { accessible: true, healthy: true, status: "pass", status_code: 200 },
      },
      guidance: ["Review <network>"],
      recommendations: [],
    },
    dependencies,
  );

  assert.equal(elements.diagnosticWebcamId.textContent, "<node>");
  assert.match(elements.diagnosticContext.textContent, /Generated at/);
  assert.match(elements.diagnosticChecksGrid.innerHTML, /&lt;invalid&gt;/);
  assert.deepEqual(state.recommendations, { guidance: ["Review <network>"], recommendations: [] });
  assert.equal(elements.copyDiagnosticReportBtn.disabled, false);
  assert.equal(state.expanded, true);
  assert.equal(elements.diagnosticPanel.focused, true);
});

test("renderDiagnosticResults supports optional summary nodes and hidden panel focus", () => {
  const { dependencies, elements } = createDependencies();
  dependencies.diagnosticOverallStatePill = null;
  dependencies.diagnosticSummaryInterpretation = null;
  dependencies.diagnosticSummaryCta = null;
  dependencies.isPanelContentVisible = () => false;

  renderDiagnosticResults({ diagnostics: {}, recommendations: [] }, dependencies);
  assert.equal(elements.diagnosticSummaryBadge.textContent, "Action required");
  assert.equal(elements.diagnosticPanel.focused, false);
});
