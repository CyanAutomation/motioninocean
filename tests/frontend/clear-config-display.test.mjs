import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

function extractClearConfigDisplay(source) {
  const match = source.match(/function clearConfigDisplay\(\) \{[\s\S]*?\n^}/m);
  if (!match) {
    throw new Error("clearConfigDisplay() definition not found");
  }
  return match[0];
}

test("clearConfigDisplay only resets .config-item .config-value nodes", () => {
  let appJs;
  try {
    appJs = fs.readFileSync("pi_camera_in_docker/static/js/app.js", "utf8");
  } catch (error) {
    throw new Error(`Failed to read app.js: ${error.message}`);
  }
  const clearConfigDisplayFn = extractClearConfigDisplay(appJs);

  const targetValueA = { textContent: "Enabled", className: "config-value config-badge enabled" };
  const targetValueB = { textContent: "42", className: "config-value highlight" };

  const structuralNodes = {
    loading: {
      id: "config-loading",
      className: "config-loading hidden",
      textContent: "",
      children: [{ id: "spinner" }],
    },
    statusIndicator: {
      id: "config-status-indicator",
      className: "config-status-dot fetching",
      textContent: "",
      children: [],
    },
    statusText: {
      id: "config-status-text",
      className: "config-status-text",
      textContent: "Fetching configuration...",
      children: [],
    },
    errorAlert: {
      id: "config-error-alert",
      className: "config-alert error hidden",
      textContent: "",
      children: [{ id: "config-error-message" }, { id: "dismiss-btn" }],
    },
    panel: {
      id: "config-panel",
      className: "config-panel hidden",
      textContent: "",
      children: [{ id: "config-loading" }, { id: "config-content" }],
    },
    lastUpdate: {
      id: "config-last-update-time",
      className: "config-timestamp-display",
      textContent: "Now",
      children: [],
    },
  };

  const structuralBefore = JSON.parse(JSON.stringify(structuralNodes));
  let selectorUsed = null;

  const context = {
    document: {
      querySelectorAll: (selector) => {
        selectorUsed = selector;
        if (selector === ".config-item .config-value") {
          return [targetValueA, targetValueB];
        }
        return [];
      },
    },
  };

  vm.runInNewContext(`${clearConfigDisplayFn}; clearConfigDisplay();`, context);

  assert.equal(selectorUsed, ".config-item .config-value");

  assert.equal(targetValueA.textContent, "--");
  assert.equal(targetValueA.className, "config-value");
  assert.equal(targetValueB.textContent, "--");
  assert.equal(targetValueB.className, "config-value");

  assert.deepEqual(structuralNodes, structuralBefore);
});
