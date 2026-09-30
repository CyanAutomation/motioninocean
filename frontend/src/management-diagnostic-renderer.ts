import {
  getDiagnosticCheckRows,
  getDiagnosticSummaryBanner,
  getDiagnosticSummaryState,
} from "./management-diagnostics.js";

type TextElement = { textContent: string; className?: string };
type HtmlElement = { innerHTML: string };

export interface DiagnosticRendererDependencies {
  diagnosticWebcamId: TextElement;
  diagnosticContext: TextElement;
  diagnosticSummaryBadge: TextElement;
  diagnosticOverallStatePill?: TextElement | null;
  diagnosticSummaryInterpretation?: TextElement | null;
  diagnosticSummaryCta?: TextElement | null;
  diagnosticChecksGrid: HtmlElement;
  diagnosticRecommendations: HtmlElement;
  copyDiagnosticReportBtn: { disabled: boolean };
  diagnosticPanel?: { focus?: () => void } | null;
  escapeHtml: (value: unknown) => string;
  renderRecommendations: (guidance: unknown[], recommendations: unknown[]) => void;
  setPanelExpanded: (isExpanded: boolean) => void;
  isPanelContentVisible: () => boolean;
  now?: () => Date;
}

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null ? (value as Record<string, unknown>) : {};
}

/** Render a diagnostic result into the management dashboard's summary panel. */
export function renderDiagnosticResults(
  diagnosticPayload: unknown,
  dependencies: DiagnosticRendererDependencies,
): void {
  const result = asRecord(diagnosticPayload);
  const nodeId = result.node_id ? String(result.node_id) : "unknown";
  const diagnostics = asRecord(result.diagnostics);
  const checkRows = getDiagnosticCheckRows(diagnostics);
  const summary = getDiagnosticSummaryState(checkRows);
  const banner = getDiagnosticSummaryBanner(summary, checkRows, diagnostics);

  dependencies.diagnosticWebcamId.textContent = nodeId;
  dependencies.diagnosticContext.textContent = `Generated at ${(dependencies.now || (() => new Date()))().toLocaleString()}`;
  dependencies.diagnosticSummaryBadge.className = `diagnostic-pill ${summary.className}`;
  dependencies.diagnosticSummaryBadge.textContent = summary.label;
  if (dependencies.diagnosticOverallStatePill) {
    dependencies.diagnosticOverallStatePill.className = `diagnostic-pill ${summary.className}`;
    dependencies.diagnosticOverallStatePill.textContent = summary.label;
  }
  if (dependencies.diagnosticSummaryInterpretation) {
    dependencies.diagnosticSummaryInterpretation.textContent = banner.interpretation;
  }
  if (dependencies.diagnosticSummaryCta) {
    dependencies.diagnosticSummaryCta.textContent = banner.cta;
  }

  dependencies.diagnosticChecksGrid.innerHTML = checkRows
    .map(
      (row) => `
        <article class="diagnostic-check-card">
          <div class="diagnostic-check-card__head">
            <h4>${dependencies.escapeHtml(row.key)}</h4>
            <span class="diagnostic-pill diagnostic-pill--${dependencies.escapeHtml(row.state)}">${dependencies.escapeHtml(
              row.state.toUpperCase(),
            )}</span>
          </div>
          <p>${dependencies.escapeHtml(row.detail)}</p>
          ${row.meta ? `<small>${dependencies.escapeHtml(row.meta)}</small>` : ""}
        </article>
      `,
    )
    .join("");

  const guidance = Array.isArray(result.guidance) ? result.guidance : [];
  const recommendations = Array.isArray(result.recommendations) ? result.recommendations : [];
  dependencies.renderRecommendations(guidance, recommendations);
  dependencies.copyDiagnosticReportBtn.disabled = false;
  dependencies.setPanelExpanded(true);
  if (dependencies.isPanelContentVisible()) {
    dependencies.diagnosticPanel?.focus?.();
  }
}
