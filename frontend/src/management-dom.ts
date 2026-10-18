/** Required page elements for the management dashboard to initialize safely. */
export const REQUIRED_MANAGEMENT_ELEMENT_IDS = [
  "webcams-table-body",
  "webcam-form",
  "form-title",
  "cancel-edit-btn",
  "refresh-webcams-btn",
  "editing-webcam-id",
  "webcam-transport",
  "copy-diagnostic-report-btn",
  "diagnostic-webcam-id",
  "diagnostic-context",
  "diagnostic-summary-badge",
  "diagnostic-checks-grid",
  "diagnostic-recommendations",
  "management-main",
  "overview-view",
  "devices-view",
  "discovered-view",
  "settings-view",
  "view-overview-btn",
  "view-devices-btn",
  "view-discovered-btn",
  "view-settings-btn",
  "theme-toggle-btn",
] as const;

/** Report missing required elements and return whether the management page can initialize. */
export function validateManagementDom(
  document: Pick<Document, "getElementById">,
  logger: { error: (message: string) => void },
  showFeedback: (message: string, isError?: boolean) => void,
): boolean {
  const missingElementIds = REQUIRED_MANAGEMENT_ELEMENT_IDS.filter(
    (id) => document.getElementById(id) == null,
  );
  if (missingElementIds.length === 0) return true;

  const details = `Missing required management UI element(s): ${missingElementIds.join(", ")}`;
  logger.error(`[management-ui] ${details}`);
  showFeedback("Management UI failed to initialize due to missing page elements.", true);
  return false;
}
