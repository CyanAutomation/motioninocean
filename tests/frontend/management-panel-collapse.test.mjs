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

test("node form panel toggle defaults expanded and flips collapsed state with storage persistence", async () => {
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
    "\n\nasync function submitNodeForm",
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
      this.listeners.set(event, handler);
    }

    setAttribute(name, value) {
      this.attributes.set(name, String(value));
    }

    getAttribute(name) {
      return this.attributes.get(name) ?? null;
    }
  }

  const localStorageReads = [];
  const localStorageWrites = [];

  const toggleNodeFormPanelBtn = new MockHTMLButtonElement();
  const managementLayout = new MockHTMLElement();
  const nodeFormPanelContainer = new MockHTMLElement();
  const nodeFormContentWrapper = new MockHTMLElement();
  const nodeFormContent = new MockHTMLElement();

  const context = {
    HTMLButtonElement: MockHTMLButtonElement,
    HTMLElement: MockHTMLElement,
    NODE_FORM_COLLAPSED_STORAGE_KEY: "management.nodeFormCollapsed",
    toggleNodeFormPanelBtn,
    managementLayout,
    nodeFormPanelContainer,
    nodeFormContentWrapper,
    nodeFormContent,
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
    nodeForm: { addEventListener: () => {} },
    cancelEditBtn: { addEventListener: () => {} },
    refreshBtn: { addEventListener: () => {} },
    tableBody: { addEventListener: () => {} },
    copyDiagnosticReportBtn: { addEventListener: () => {} },
    submitNodeForm: () => {},
    resetForm: () => {},
    showFeedback: () => {},
    stopStatusRefreshInterval: () => {},
    fetchNodes: async () => {},
    refreshStatuses: async () => {},
    startStatusRefreshInterval: () => {},
    onTableClick: () => {},
    updateBaseUrlValidation: () => {},
    buildDiagnosticTextReport: () => "",
    document: {
      getElementById: () => ({
        addEventListener: () => {},
        value: "http",
      }),
    },
  };

  vm.runInNewContext(
    `${setNodeFormPanelCollapsedFn};\n${toggleNodeFormPanelFn};\n${getStoredNodeFormCollapsedPreferenceFn};\n${initFn};`,
    context,
  );

  await context.init();

  assert.deepEqual(localStorageReads, ["management.nodeFormCollapsed"]);
  assert.equal(toggleNodeFormPanelBtn.getAttribute("aria-expanded"), "true");
  assert.equal(toggleNodeFormPanelBtn.textContent, "«");
  assert.equal(toggleNodeFormPanelBtn.title, "Collapse node form panel");
  assert.equal(managementLayout.classList.contains("is-form-collapsed"), false);
  assert.equal(nodeFormPanelContainer.classList.contains("is-form-collapsed"), false);
  assert.equal(nodeFormContent.classList.contains("hidden"), false);

  const toggleHandler = toggleNodeFormPanelBtn.listeners.get("click");
  assert.equal(typeof toggleHandler, "function");

  toggleHandler();

  assert.equal(managementLayout.classList.contains("is-form-collapsed"), true);
  assert.equal(nodeFormPanelContainer.classList.contains("is-form-collapsed"), true);
  assert.equal(nodeFormContent.classList.contains("hidden"), true);
  assert.equal(toggleNodeFormPanelBtn.getAttribute("aria-expanded"), "false");
  assert.equal(toggleNodeFormPanelBtn.textContent, "»");
  assert.equal(toggleNodeFormPanelBtn.title, "Expand node form panel");

  toggleHandler();

  assert.equal(managementLayout.classList.contains("is-form-collapsed"), false);
  assert.equal(nodeFormPanelContainer.classList.contains("is-form-collapsed"), false);
  assert.equal(nodeFormContent.classList.contains("hidden"), false);
  assert.equal(toggleNodeFormPanelBtn.getAttribute("aria-expanded"), "true");
  assert.equal(toggleNodeFormPanelBtn.textContent, "«");
  assert.equal(toggleNodeFormPanelBtn.title, "Collapse node form panel");

  assert.deepEqual(localStorageWrites, [
    ["management.nodeFormCollapsed", "false"],
    ["management.nodeFormCollapsed", "true"],
    ["management.nodeFormCollapsed", "false"],
  ]);
});
