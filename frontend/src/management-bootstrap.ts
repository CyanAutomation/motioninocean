/**
 * Event binding and startup orchestration for the management dashboard.
 *
 * The feature logic remains in management.js for now, but the bootstrap has
 * no knowledge of its globals. All behavior is supplied through the context
 * object, which keeps startup wiring independently testable.
 */

interface DashboardElement extends HTMLElement {
  value?: string;
}

interface ButtonCollection {
  forEach(callback: (button: unknown) => void): void;
}

interface DashboardElements {
  [key: string]: DashboardElement | ButtonCollection | null | undefined;
  settingsTabButtons?: ButtonCollection;
  webcamForm: DashboardElement;
  cancelEditBtn: DashboardElement;
  refreshBtn: DashboardElement;
  tableBody: DashboardElement;
  webcamTransport: DashboardElement;
  diagnosticsAdvancedCheckbox?: DashboardElement;
  diagnosticsCollapsibleContainer?: DashboardElement;
}

interface DashboardActions {
  setActiveView: (view: string) => void;
  openHelpPanel: () => void;
  openExportPanel: () => void;
  closeUtilityPanel: () => void;
  toggleTheme: () => void;
  submitNodeForm: (event: Event) => void;
  resetForm: () => void;
  refreshManagementData: () => Promise<unknown>;
  showFeedback: (message: string, isError?: boolean) => void;
  startStatusRefreshInterval: () => void;
  stopStatusRefreshInterval: () => void;
  renderOverviewPanel: () => void;
  scanDiscoveredBtn?: () => void;
  renderDiscoveredPanel: () => void;
  setDiscoveredFeedback: (message: string, isError?: boolean) => void;
  selectDiscoveredNode: (nodeId: string) => void;
  applyDiscoveredDecision: (decision: "approve" | "reject" | "snooze") => Promise<unknown>;
  fetchOverview: () => Promise<unknown>;
  setSettingsTab: (tabName: string) => void;
  saveSettings: () => void | Promise<void>;
  resetSettings: () => void | Promise<void>;
  fetchSettingsData: () => void | Promise<void>;
  setNodeFormPanelCollapsed: (isCollapsed: boolean) => void;
  getStoredNodeFormCollapsedPreference: () => boolean;
  toggleNodeFormPanel: () => void;
  onTableClick: (event: Event) => void;
  updateBaseUrlValidation: (transport: string) => void;
  setDiagnosticPanelExpanded: (isExpanded: boolean) => void;
  toggleDiagnosticPanelContent: () => void;
  getViewFromLocationHash: () => string;
  initializeManagementState: () => void;
  bindManagementNavigation: () => void;
  fetchWebcams: () => Promise<unknown>;
  refreshStatuses: () => Promise<unknown>;
  getLatestDiagnosticResult: () => unknown;
  buildDiagnosticTextReport: (result: unknown) => string;
}

interface DashboardContext {
  elements: DashboardElements;
  actions: DashboardActions;
}

interface NavigationContext {
  elements: Partial<DashboardElements>;
  actions: Pick<
    DashboardActions,
    | "closeUtilityPanel"
    | "getViewFromLocationHash"
    | "openExportPanel"
    | "openHelpPanel"
    | "setActiveView"
    | "toggleTheme"
  >;
}

interface DiagnosticClipboardActions {
  getLatestDiagnosticResult: () => unknown;
  showFeedback: (message: string, isError?: boolean) => void;
  buildDiagnosticTextReport: (result: unknown) => string;
}

function isButton(element: unknown): element is DashboardElement {
  return (
    element != null &&
    typeof element === "object" &&
    typeof (element as { addEventListener?: unknown }).addEventListener === "function" &&
    (typeof HTMLButtonElement === "undefined" || element instanceof HTMLButtonElement)
  );
}

function isElement(element: unknown): element is DashboardElement {
  return (
    element != null &&
    typeof element === "object" &&
    (typeof HTMLElement === "undefined" || element instanceof HTMLElement)
  );
}

/**
 * Copy the latest diagnostic report and provide user-facing failure feedback.
 *
 * @param {Object} actions - Diagnostic callbacks.
 * @returns {Promise<void>} Resolves after the copy attempt completes.
 */
export async function copyDiagnosticReport(actions: DiagnosticClipboardActions): Promise<void> {
  const diagnosticResult = actions.getLatestDiagnosticResult();
  if (!diagnosticResult) {
    actions.showFeedback("Run Diagnose first to generate a report.", true);
    return;
  }

  if (typeof globalThis.navigator?.clipboard?.writeText !== "function") {
    actions.showFeedback("Clipboard not available in this browser.", true);
    return;
  }

  try {
    await globalThis.navigator.clipboard.writeText(
      actions.buildDiagnosticTextReport(diagnosticResult),
    );
    actions.showFeedback("Diagnostic report copied to clipboard.");
  } catch {
    actions.showFeedback("Could not copy report to clipboard.", true);
  }
}

function bindOptionalButton(
  button: unknown,
  eventName: string,
  handler: () => void | Promise<void>,
): void {
  if (isButton(button)) {
    button.addEventListener(eventName, handler);
  }
}

/**
 * Bind navigation and utility controls.
 *
 * @param {Object} context - Dashboard bootstrap context.
 * @param {Object} context.elements - DOM elements used by navigation.
 * @param {Object} context.actions - Navigation and utility callbacks.
 * @returns {void}
 */
export function bindNavigation({ elements, actions }: NavigationContext): void {
  const viewButtons = [
    [elements.viewOverviewBtn, "overview"],
    [elements.viewDevicesBtn, "devices"],
    [elements.viewDiscoveredBtn, "discovered"],
    [elements.viewSettingsBtn, "settings"],
    [elements.railOverviewBtn, "overview"],
    [elements.railDevicesBtn, "devices"],
    [elements.railDiscoveredBtn, "discovered"],
    [elements.railSettingsBtn, "settings"],
    [elements.mobileOverviewBtn, "overview"],
    [elements.mobileDevicesBtn, "devices"],
    [elements.mobileDiscoveredBtn, "discovered"],
    [elements.mobileSettingsBtn, "settings"],
  ] as const;

  viewButtons.forEach(([button, view]) => {
    bindOptionalButton(button, "click", () => actions.setActiveView(view));
  });

  const utilityButtons = [
    [elements.railHelpBtn, actions.openHelpPanel],
    [elements.mobileHelpBtn, actions.openHelpPanel],
    [elements.railExportBtn, actions.openExportPanel],
    [elements.mobileExportBtn, actions.openExportPanel],
    [elements.utilityPanelCloseBtn, actions.closeUtilityPanel],
    [elements.themeToggleBtn, actions.toggleTheme],
  ] as const;
  utilityButtons.forEach(([button, handler]) => {
    bindOptionalButton(button, "click", handler);
  });

  if (typeof globalThis.addEventListener === "function") {
    globalThis.addEventListener("hashchange", () => {
      actions.setActiveView(actions.getViewFromLocationHash());
    });
  }
}

/**
 * Bind dashboard controls that are not part of navigation.
 *
 * @param {Object} context - Dashboard bootstrap context.
 * @param {Object} context.elements - Dashboard DOM elements.
 * @param {Object} context.actions - Dashboard callbacks.
 * @returns {void}
 */
export function bindDashboardControls({ elements, actions }: DashboardContext): void {
  elements.webcamForm.addEventListener("submit", actions.submitNodeForm);
  elements.cancelEditBtn.addEventListener("click", () => {
    actions.resetForm();
    actions.showFeedback("");
  });

  elements.refreshBtn.addEventListener("click", async () => {
    actions.stopStatusRefreshInterval();
    try {
      await actions.refreshManagementData();
      actions.showFeedback("Node list refreshed.");
    } finally {
      actions.startStatusRefreshInterval();
    }
  });

  bindOptionalButton(elements.refreshDashboardBtn, "click", async () => {
    await actions.refreshManagementData();
    actions.renderOverviewPanel();
  });

  bindOptionalButton(elements.scanDiscoveredBtn, "click", async () => {
    await actions.refreshManagementData();
    actions.renderDiscoveredPanel();
    actions.setDiscoveredFeedback("Discovery queue refreshed.");
  });

  if (isElement(elements.discoveredList)) {
    elements.discoveredList.addEventListener("click", (event) => {
      const target = event.target;
      if (!isElement(target)) {
        return;
      }
      const button = target.closest("[data-discovered-id]");
      if (!isElement(button) || !button.dataset.discoveredId) {
        return;
      }
      actions.selectDiscoveredNode(button.dataset.discoveredId);
      actions.renderDiscoveredPanel();
    });
  }

  bindOptionalButton(elements.discoveredApproveBtn, "click", async () => {
    await actions.applyDiscoveredDecision("approve");
    await actions.fetchOverview();
  });
  bindOptionalButton(elements.discoveredRejectBtn, "click", async () => {
    await actions.applyDiscoveredDecision("reject");
    await actions.fetchOverview();
  });
  bindOptionalButton(elements.discoveredLaterBtn, "click", async () => {
    await actions.applyDiscoveredDecision("snooze");
    await actions.fetchOverview();
  });

  if (elements.settingsTabButtons && typeof elements.settingsTabButtons.forEach === "function") {
    elements.settingsTabButtons.forEach((button) => {
      if (isButton(button)) {
        button.addEventListener("click", () => {
          actions.setSettingsTab(button.dataset.settingsTab || "auth");
        });
      }
    });
  }
  bindOptionalButton(elements.settingsSaveBtn, "click", actions.saveSettings);
  bindOptionalButton(elements.settingsResetBtn, "click", actions.resetSettings);
  bindOptionalButton(elements.refreshSettingsBtn, "click", actions.fetchSettingsData);

  if (isButton(elements.toggleWebcamFormPanelBtn) && isElement(elements.webcamFormContent)) {
    actions.setNodeFormPanelCollapsed(actions.getStoredNodeFormCollapsedPreference());
    elements.toggleWebcamFormPanelBtn.addEventListener("click", actions.toggleNodeFormPanel);
  }

  elements.tableBody.addEventListener("click", actions.onTableClick);
  elements.webcamTransport.addEventListener("change", (event) => {
    if (typeof HTMLSelectElement === "undefined" || !(event.target instanceof HTMLSelectElement)) {
      return;
    }
    actions.updateBaseUrlValidation(event.target.value);
  });
  actions.updateBaseUrlValidation(elements.webcamTransport.value || "");

  if (elements.diagnosticsAdvancedCheckbox && elements.diagnosticsCollapsibleContainer) {
    actions.setDiagnosticPanelExpanded(false);
    elements.diagnosticsAdvancedCheckbox.addEventListener(
      "change",
      actions.toggleDiagnosticPanelContent,
    );
  }

  bindOptionalButton(elements.copyDiagnosticReportBtn, "click", () =>
    copyDiagnosticReport(actions),
  );
}

/**
 * Bind controls and load the initial management dashboard state.
 *
 * @param {Object} context - Dashboard bootstrap context.
 * @returns {Promise<void>} Resolves after initial data has loaded.
 */
export async function initializeManagementDashboard(context: DashboardContext): Promise<void> {
  const { actions } = context;
  actions.initializeManagementState();
  actions.bindManagementNavigation();
  bindDashboardControls(context);

  actions.setSettingsTab("auth");
  actions.setActiveView(actions.getViewFromLocationHash());
  await actions.fetchWebcams();
  await actions.refreshStatuses();
  await actions.fetchOverview();
  await actions.fetchSettingsData();
  actions.renderDiscoveredPanel();
  actions.renderOverviewPanel();
  actions.startStatusRefreshInterval();
}
