import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import ts from "typescript";

function extractUtilityPanelHelpers(source: string): string {
  const start = source.indexOf("function openUtilityPanel");
  const end = source.indexOf("\n/**\n * Fetch from management API", start);
  if (start === -1 || end === -1) {
    throw new Error("utility panel helpers not found");
  }
  return source.slice(start, end).trim();
}

class MockElement {
  className = "";
  textContent = "";
  innerHTML = "";
  children: MockElement[] = [];
  classList = {
    removed: new Set<string>(),
    remove(name: string) {
      this.removed.add(name);
    },
  };

  constructor(readonly tagName: string) {}

  append(...nodes: MockElement[]) {
    this.children.push(...nodes);
  }

  appendChild(node: MockElement) {
    this.children.push(node);
    return node;
  }

  replaceChildren(...nodes: MockElement[]) {
    this.children = [...nodes];
  }
}

function createUtilityPanelContext() {
  const utilityPanel = new MockElement("aside");
  const utilityPanelTitle = new MockElement("h2");
  const utilityPanelContent = new MockElement("div");
  const source = fs.readFileSync("frontend/src/management.ts", "utf8");
  const transpiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const helpers = extractUtilityPanelHelpers(transpiled);
  const context = {
    HTMLElement: MockElement,
    document: {
      createElement: (tagName: string) => new MockElement(tagName),
    },
    utilityPanel,
    utilityPanelTitle,
    utilityPanelContent,
    latestDiagnosticResult: null as unknown,
    buildDiagnosticTextReport: () => "",
    escapeHtml: (value: unknown) => String(value),
  };

  vm.runInNewContext(`${helpers};`, context);
  return context as typeof context & {
    openHelpPanel(): void;
    openExportPanel(): void;
  };
}

test("help utility panel builds its content with DOM text nodes", () => {
  const context = createUtilityPanelContext();

  context.openHelpPanel();

  const list = context.utilityPanelContent.children[0];
  assert.ok(list);
  assert.equal(list.tagName, "ul");
  assert.equal(list.children.length, 5);
  assert.match(list.children[0].textContent, /Browser → Management/);
  assert.equal(context.utilityPanelContent.innerHTML, "");
  assert.equal(context.utilityPanel.classList.removed.has("hidden"), true);
});

test("diagnostic utility panel renders attacker-controlled report text without parsing markup", () => {
  const context = createUtilityPanelContext();
  const untrustedReport = '<img src=x onerror="alert(1)">';
  context.latestDiagnosticResult = { node_id: "remote-node" };
  context.buildDiagnosticTextReport = () => untrustedReport;

  context.openExportPanel();

  const contentWrapper = context.utilityPanelContent.children[0];
  assert.ok(contentWrapper);
  const report = contentWrapper.children.find((child) => child.tagName === "pre");
  assert.ok(report);
  assert.equal(report.textContent, untrustedReport);
  assert.equal(context.utilityPanelContent.innerHTML, "");
});

test("missing diagnostic report is rendered as text content", () => {
  const context = createUtilityPanelContext();

  context.openExportPanel();

  const message = context.utilityPanelContent.children[0];
  assert.ok(message);
  assert.equal(message.tagName, "p");
  assert.equal(message.textContent, "No diagnostic report is available yet. Run Diagnose for any node first.");
  assert.equal(context.utilityPanelContent.innerHTML, "");
});
