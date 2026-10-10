import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { asTestDouble } from "./test-doubles.ts";

function extractFunction(source: string, functionName: string): string {
  const match = source.match(
    new RegExp(`function ${functionName}\\([^)]*\\) \\{[\\s\\S]*?\\n^}`, "m"),
  );
  if (!match) {
    throw new Error(`${functionName}() definition not found`);
  }
  return match[0];
}

test("applyTheme updates document theme, icons, and storage", () => {
  const appJs = fs.readFileSync("pi_camera_in_docker/static/js/app.js", "utf8");
  const applyThemeFn = extractFunction(appJs, "applyTheme");

  const writes: Array<[string, string]> = [];
  const moonStyle = { display: "" };
  const sunStyle = { display: "" };
  const context = {
    THEME_STORAGE_KEY: "webcam.theme",
    document: {
      documentElement: {
        attributes: {} as Record<string, string>,
        setAttribute(name: string, value: string) {
          this.attributes[name] = value;
        },
      },
    },
    state: {
      elements: {
        themeIconMoon: { style: moonStyle },
        themeIconSun: { style: sunStyle },
      },
    },
    localStorage: {
      setItem(key: string, value: string) {
        writes.push([key, value]);
      },
    },
  };

  vm.runInNewContext(`${applyThemeFn};`, context);
  asTestDouble<typeof context & { applyTheme(theme: string): void }>(context).applyTheme("dark");

  assert.equal(context.document.documentElement.attributes["data-theme"], "dark");
  assert.equal(moonStyle.display, "none");
  assert.equal(sunStyle.display, "");
  assert.deepEqual(writes, [["webcam.theme", "dark"]]);
});

test("initializeTheme loads persisted preference and calls applyTheme", () => {
  const appJs = fs.readFileSync("pi_camera_in_docker/static/js/app.js", "utf8");
  const initializeThemeFn = extractFunction(appJs, "initializeTheme");

  const calls: string[] = [];
  const context = {
    THEME_STORAGE_KEY: "webcam.theme",
    localStorage: {
      getItem() {
        return "dark";
      },
    },
    applyTheme: (theme: string) => {
      calls.push(theme);
    },
  };

  vm.runInNewContext(`${initializeThemeFn};`, context);
  asTestDouble<typeof context & { initializeTheme(): void }>(context).initializeTheme();

  assert.deepEqual(calls, ["dark"]);
});
