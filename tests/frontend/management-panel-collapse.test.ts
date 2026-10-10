import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import ts from "typescript";
import { bindDashboardControls } from "../../frontend/src/management-bootstrap.ts";
import { asTestDouble } from "./test-doubles.ts";

type MockEventListener = ((event: Event) => void) | { handleEvent(event: Event): void };

function extractFunction(source: string, signature: string, nextSignature: string): string {
  const start = source.indexOf(signature);
  const end = source.indexOf(nextSignature, start);
  if (start === -1 || end === -1) {
    throw new Error(`${signature} definition not found`);
  }
  return source.slice(start, end).trim();
}

function createClassList() {
  const classes = new Set<string>();
  return {
    toggle: (className: string, force?: boolean) => {
      const shouldHave = force ?? !classes.has(className);
      if (shouldHave) {
        classes.add(className);
      } else {
        classes.delete(className);
      }
      return shouldHave;
    },
    add: (className: string) => {
      classes.add(className);
    },
    contains: (className: string) => classes.has(className),
  };
}

test("webcam form panel toggle defaults expanded and flips collapsed state with storage persistence", async () => {
  const managementSource = fs.readFileSync("frontend/src/management.ts", "utf8");
  const managementJs = ts.transpileModule(managementSource, {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  }).outputText;

  const setNodeFormPanelCollapsedFn = extractFunction(
    managementJs,
    "function setNodeFormPanelCollapsed",
    "\nfunction toggleNodeFormPanel",
  );
  const toggleNodeFormPanelFn = extractFunction(
    managementJs,
    "function toggleNodeFormPanel",
    "\nfunction getStoredNodeFormCollapsedPreference",
  );
  const getStoredNodeFormCollapsedPreferenceFn = extractFunction(
    managementJs,
    "function getStoredNodeFormCollapsedPreference",
    "\nasync function submitNodeForm",
  );

  class MockHTMLElement {
    classList = createClassList();

    constructor() {
      this.classList = createClassList();
    }
  }

  class MockHTMLButtonElement extends MockHTMLElement {
    attributeValues = new Map<string, string>();
    textContent = "";
    title = "";
    listeners = new Map<string, Array<(event: Event) => void>>();

    constructor() {
      super();
    }

    addEventListener(event: string, handler: MockEventListener) {
      if (!this.listeners.has(event)) {
        this.listeners.set(event, []);
      }
      this.listeners
        .get(event)
        ?.push(typeof handler === "function" ? handler : (event) => handler.handleEvent(event));
    }

    setAttribute(name: string, value: string) {
      this.attributeValues.set(name, String(value));
    }

    getAttribute(name: string) {
      return this.attributeValues.get(name) ?? null;
    }
  }

  class MockHTMLInputElement extends MockHTMLElement {}

  const localStorageReads: string[] = [];
  const localStorageWrites: Array<[string, string]> = [];

  const toggleWebcamFormPanelBtn = new MockHTMLButtonElement();
  const managementLayout = new MockHTMLElement();
  const webcamFormPanelContainer = new MockHTMLElement();
  const webcamFormContentWrapper = new MockHTMLElement();
  const webcamFormContent = new MockHTMLElement();

  const context = {
    HTMLButtonElement: MockHTMLButtonElement,
    HTMLInputElement: MockHTMLInputElement,
    HTMLElement: MockHTMLElement,
    NODE_FORM_COLLAPSED_STORAGE_KEY: "management.webcamFormCollapsed",
    toggleWebcamFormPanelBtn,
    managementLayout,
    webcamFormPanelContainer,
    webcamFormContentWrapper,
    webcamFormContent,
    globalThis: {
      localStorage: {
        getItem: (key: string) => {
          localStorageReads.push(key);
          return "false";
        },
        setItem: (key: string, value: string) => {
          localStorageWrites.push([key, value]);
        },
      },
    },
    webcamForm: { addEventListener: () => {} },
    formTitle: { textContent: "" },
    editingWebcamIdInput: { value: "" },
    cancelEditBtn: { addEventListener: () => {} },
    refreshBtn: { addEventListener: () => {} },
    tableBody: { addEventListener: () => {} },
    diagnosticsAdvancedCheckbox: undefined,
    diagnosticsCollapsibleContainer: undefined,
    copyDiagnosticReportBtn: { addEventListener: () => {} },
    getMissingRequiredElementIds: () => [],
    submitNodeForm: () => {},
    resetForm: () => {},
    showFeedback: () => {},
    stopStatusRefreshInterval: () => {},
    fetchWebcams: async () => {},
    refreshStatuses: async () => {},
    startStatusRefreshInterval: () => {},
    onTableClick: () => {},
    updateBaseUrlValidation: () => {},
    buildDiagnosticTextReport: () => "",
    setNodeFormPanelCollapsed: undefined,
    toggleNodeFormPanel: undefined,
    getStoredNodeFormCollapsedPreference: undefined,
    console: { error: () => {} },
    document: {
      getElementById: () => ({
        addEventListener: () => {},
        value: "http",
        disabled: false,
      }),
    },
  };

  vm.runInNewContext(
    `${setNodeFormPanelCollapsedFn};\n${toggleNodeFormPanelFn};\n${getStoredNodeFormCollapsedPreferenceFn};`,
    context,
  );

  const evaluatedContext = asTestDouble<{
    setNodeFormPanelCollapsed: (isCollapsed: boolean) => void;
    toggleNodeFormPanel: () => void;
    getStoredNodeFormCollapsedPreference: () => boolean;
  }>(context);

  bindDashboardControls(
    asTestDouble<Parameters<typeof bindDashboardControls>[0]>({
      elements: {
        webcamForm: context.webcamForm,
        cancelEditBtn: context.cancelEditBtn,
        refreshBtn: context.refreshBtn,
        tableBody: context.tableBody,
        webcamTransport: context.document.getElementById(),
        toggleWebcamFormPanelBtn,
        webcamFormContent,
        copyDiagnosticReportBtn: context.copyDiagnosticReportBtn,
        diagnosticsAdvancedCheckbox: undefined,
        diagnosticsCollapsibleContainer: undefined,
        settingsTabButtons: [],
      },
      actions: {
        submitNodeForm: context.submitNodeForm,
        resetForm: context.resetForm,
        showFeedback: context.showFeedback,
        stopStatusRefreshInterval: context.stopStatusRefreshInterval,
        refreshManagementData: async () => {},
        startStatusRefreshInterval: context.startStatusRefreshInterval,
        renderOverviewPanel: () => {},
        renderDiscoveredPanel: () => {},
        setDiscoveredFeedback: () => {},
        selectDiscoveredNode: () => {},
        applyDiscoveredDecision: async () => {},
        fetchOverview: async () => {},
        setSettingsTab: () => {},
        saveSettings: async () => {},
        resetSettings: async () => {},
        fetchSettingsData: async () => {},
        setNodeFormPanelCollapsed: evaluatedContext.setNodeFormPanelCollapsed,
        getStoredNodeFormCollapsedPreference: evaluatedContext.getStoredNodeFormCollapsedPreference,
        toggleNodeFormPanel: evaluatedContext.toggleNodeFormPanel,
        onTableClick: context.onTableClick,
        updateBaseUrlValidation: context.updateBaseUrlValidation,
        setDiagnosticPanelExpanded: () => {},
        toggleDiagnosticPanelContent: () => {},
        getLatestDiagnosticResult: () => null,
        buildDiagnosticTextReport: () => "",
      },
    }),
  );

  assert.deepEqual(localStorageReads, ["management.webcamFormCollapsed"]);
  assert.equal(toggleWebcamFormPanelBtn.getAttribute("aria-expanded"), "true");
  assert.equal(toggleWebcamFormPanelBtn.textContent, "«");
  assert.equal(toggleWebcamFormPanelBtn.title, "Collapse webcam form panel");
  assert.equal(managementLayout.classList.contains("is-form-collapsed"), false);
  assert.equal(webcamFormPanelContainer.classList.contains("is-form-collapsed"), false);
  assert.equal(webcamFormContent.classList.contains("hidden"), false);

  const toggleHandler = toggleWebcamFormPanelBtn.listeners.get("click")?.[0];
  assert.equal(typeof toggleHandler, "function");
  assert.ok(toggleHandler);

  toggleHandler(new Event("click"));

  assert.equal(managementLayout.classList.contains("is-form-collapsed"), true);
  assert.equal(webcamFormPanelContainer.classList.contains("is-form-collapsed"), true);
  assert.equal(webcamFormContent.classList.contains("hidden"), true);
  assert.equal(toggleWebcamFormPanelBtn.getAttribute("aria-expanded"), "false");
  assert.equal(toggleWebcamFormPanelBtn.textContent, "»");
  assert.equal(toggleWebcamFormPanelBtn.title, "Expand webcam form panel");

  toggleHandler(new Event("click"));

  assert.equal(managementLayout.classList.contains("is-form-collapsed"), false);
  assert.equal(webcamFormPanelContainer.classList.contains("is-form-collapsed"), false);
  assert.equal(webcamFormContent.classList.contains("hidden"), false);
  assert.equal(toggleWebcamFormPanelBtn.getAttribute("aria-expanded"), "true");
  assert.equal(toggleWebcamFormPanelBtn.textContent, "«");
  assert.equal(toggleWebcamFormPanelBtn.title, "Collapse webcam form panel");

  assert.deepEqual(localStorageWrites, [
    ["management.webcamFormCollapsed", "false"],
    ["management.webcamFormCollapsed", "true"],
    ["management.webcamFormCollapsed", "false"],
  ]);
});
