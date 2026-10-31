import test from "node:test";
import assert from "node:assert/strict";
import { clearConfigDisplay, type ConfigDisplayValue } from "../../frontend/src/config-display.ts";

test("clearConfigDisplay only resets dedicated config value nodes", () => {
  const attributesA: Record<string, string> = { title: "Enabled state" };
  const targetValueA: ConfigDisplayValue = {
    id: "config-camera-enabled",
    textContent: "Enabled",
    className: "config-value config-badge enabled",
    classList: { add: (..._names: string[]) => {} },
    setAttribute: (name, value) => {
      attributesA[name] = value;
    },
    removeAttribute: (name) => {
      delete attributesA[name];
    },
  };
  const attributesB: Record<string, string> = {
    title: "Camera is healthy",
    "data-health-state": "healthy",
  };
  const healthValue: ConfigDisplayValue = {
    id: "config-health-camera",
    textContent: "42",
    className: "config-value health-indicator health-ok",
    classList: {
      add: (...names) => {
        const classes = new Set(healthValue.className.split(" "));
        names.forEach((name) => classes.add(name));
        healthValue.className = [...classes].join(" ");
      },
    },
    setAttribute: (name, value) => {
      attributesB[name] = value;
    },
    removeAttribute: (name) => {
      delete attributesB[name];
    },
  };
  const state = { streamConnections: { current: "5", max: "10" } };
  let connectionDisplaysUpdated = 0;

  clearConfigDisplay(
    {
      querySelectorAll: () => [targetValueA, healthValue],
    },
    state,
    () => {
      connectionDisplaysUpdated += 1;
    },
  );

  assert.equal(targetValueA.textContent, "--");
  assert.equal(targetValueA.className, "config-value");
  assert.deepEqual(attributesA, {});
  assert.equal(healthValue.textContent, "--");
  assert.equal(healthValue.className, "config-value health-indicator health-unknown");
  assert.deepEqual(attributesB, { "data-health-state": "unknown" });
  assert.deepEqual(state.streamConnections, { current: "--", max: "--" });
  assert.equal(connectionDisplaysUpdated, 1);
});
