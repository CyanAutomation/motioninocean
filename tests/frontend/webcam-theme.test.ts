import test from "node:test";
import assert from "node:assert/strict";

import { createWebcamThemeController } from "../../frontend/src/webcam-theme.ts";

test("webcam theme controller updates the document, icon pair, and saved preference", () => {
  const attributes: Record<string, string> = {};
  const writes: Array<[string, string]> = [];
  const moonStyle = { display: "" };
  const sunStyle = { display: "" };
  const controller = createWebcamThemeController({
    getRoot: () => ({
      setAttribute(name, value) {
        attributes[name] = value;
      },
    }),
    getStorage: () => ({
      getItem: () => null,
      setItem: (key, value) => writes.push([key, value]),
    }),
    getIcons: () => ({ moon: { style: moonStyle }, sun: { style: sunStyle } }),
  });

  controller.applyTheme("dark");

  assert.equal(attributes["data-theme"], "dark");
  assert.equal(moonStyle.display, "none");
  assert.equal(sunStyle.display, "");
  assert.deepEqual(writes, [["webcam.theme", "dark"]]);
});

test("webcam theme controller defaults to light and tolerates unavailable storage", () => {
  const attributes: Record<string, string> = {};
  const moonStyle = { display: "" };
  const sunStyle = { display: "" };
  const controller = createWebcamThemeController({
    getRoot: () => ({
      setAttribute(name, value) {
        attributes[name] = value;
      },
    }),
    getStorage: () => {
      throw new Error("Storage unavailable");
    },
    getIcons: () => ({ moon: { style: moonStyle }, sun: { style: sunStyle } }),
  });

  controller.initializeTheme();

  assert.equal(attributes["data-theme"], "light");
  assert.equal(moonStyle.display, "");
  assert.equal(sunStyle.display, "none");
});
