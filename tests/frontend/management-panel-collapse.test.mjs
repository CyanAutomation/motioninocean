import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

function extractFunction(source, signature, nextSignature) {
  const start = source.indexOf(signature);
  const end = source.indexOf(nextSignature, start);
  if (start === -1 || end === -1) {
    throw new Error(`${signature} definition not found`);
  }
  return source.slice(start, end).trim();
}

function extractInit(source) {
  const start = source.indexOf("async function init()");
  const end = source.indexOf("\n\ninit().catch", start);
  if (start === -1 || end === -1) {
    throw new Error("init() definition not found");
  }
  return source.slice(start, end).trim();
}

function createClassList() {
  const classes = new Set();
  return {
    toggle: (className, force) => {
      const shouldHave = force ?? !classes.has(className);
      if (shouldHave) {
        classes.add(className);
      } else {
        classes.delete(className);
      }
    },
    add: (className) => classes.add(className),
    contains: (className) => classes.has(className),
  };
}

test("webcam form panel toggle defaults expanded and flips collapsed state with storage persistence", async () => {
  const managementJs = fs.readFileSync("pi_camera_in_docker/static/js/management.js", "utf8");

  const setNodeFormPanelCollapsedFn = extractFunction(
    managementJs,
    "function setNodeFormPanelCollapsed",
    "\n\nfunction toggleNodeFormPanel",
  );
  const toggleNodeFormPanelFn = extractFunction(
    managementJs,
    "function toggleNodeFormPanel",
    "\n\nfunction getStoredNodeFormCollapsedPreference",
  );
  const getStoredNodeFormCollapsedPreferenceFn = extractFunction(
    managementJs,
    "function getStoredNodeFormCollapsedPreference",
    "\n\n/**\n * Submit webcam form (create or update).",
  );
  const initFn = extractInit(managementJs);

  class MockHTMLElement {
    constructor() {
      this.classList = createClassList();
    }
  }

  class MockHTMLButtonElement extends MockHTMLElement {
    constructor() {
      super();
      this.attributes = new Map();
      this.textContent = "";
      this.title = "";
      this.listeners = new Map();
    }

    addEventListener(event, handler) {
      if (!this.listeners.has(event)) {
        this.listeners.set(event, []);
      }
      this.listeners.get(event).push(handler);
    }

    setAttribute(name, value) {
      this.attributes.set(name, String(value));
    }

    getAttribute(name) {
      return this.attributes.get(name) ?? null;
    }
  }

  class MockHTMLInputElement extends MockHTMLElement {}

  const localStorageReads = [];
  const localStorageWrites = [];

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
        getItem: (key) => {
          localStorageReads.push(key);
          return "false";
        },
        setItem: (key, value) => {
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
    diagnosticsAdvancedCheckbox: null,
    diagnosticsCollapsibleContainer: null,
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
    `${setNodeFormPanelCollapsedFn};\n${toggleNodeFormPanelFn};\n${getStoredNodeFormCollapsedPreferenceFn};\n${initFn};`,
    context,
  );

  await context.init();

  assert.deepEqual(localStorageReads, ["management.webcamFormCollapsed"]);
  assert.equal(toggleWebcamFormPanelBtn.getAttribute("aria-expanded"), "true");
  assert.equal(toggleWebcamFormPanelBtn.textContent, "«");
  assert.equal(toggleWebcamFormPanelBtn.title, "Collapse webcam form panel");
  assert.equal(managementLayout.classList.contains("is-form-collapsed"), false);
  assert.equal(webcamFormPanelContainer.classList.contains("is-form-collapsed"), false);
  assert.equal(webcamFormContent.classList.contains("hidden"), false);

  const toggleHandler = toggleWebcamFormPanelBtn.listeners.get("click")?.[0];
  assert.equal(typeof toggleHandler, "function");

  toggleHandler();

  assert.equal(managementLayout.classList.contains("is-form-collapsed"), true);
  assert.equal(webcamFormPanelContainer.classList.contains("is-form-collapsed"), true);
  assert.equal(webcamFormContent.classList.contains("hidden"), true);
  assert.equal(toggleWebcamFormPanelBtn.getAttribute("aria-expanded"), "false");
  assert.equal(toggleWebcamFormPanelBtn.textContent, "»");
  assert.equal(toggleWebcamFormPanelBtn.title, "Expand webcam form panel");

  toggleHandler();

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
