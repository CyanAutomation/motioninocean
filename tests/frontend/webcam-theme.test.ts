import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

function extractFunction(source, functionName) {
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

  const writes = [];
  const moonStyle = { display: "" };
  const sunStyle = { display: "" };
  const context = {
    THEME_STORAGE_KEY: "webcam.theme",
    document: {
      documentElement: {
        attributes: {},
        setAttribute(name, value) {
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
      setItem(key, value) {
        writes.push([key, value]);
      },
    },
  };

  vm.runInNewContext(`${applyThemeFn};`, context);
  context.applyTheme("dark");

  assert.equal(context.document.documentElement.attributes["data-theme"], "dark");
  assert.equal(moonStyle.display, "none");
  assert.equal(sunStyle.display, "");
  assert.deepEqual(writes, [["webcam.theme", "dark"]]);
});

test("initializeTheme loads persisted preference and calls applyTheme", () => {
  const appJs = fs.readFileSync("pi_camera_in_docker/static/js/app.js", "utf8");
  const initializeThemeFn = extractFunction(appJs, "initializeTheme");

  const calls = [];
  const context = {
    THEME_STORAGE_KEY: "webcam.theme",
    localStorage: {
      getItem() {
        return "dark";
      },
    },
    applyTheme: (theme) => {
      calls.push(theme);
    },
  };

  vm.runInNewContext(`${initializeThemeFn};`, context);
  context.initializeTheme();

  assert.deepEqual(calls, ["dark"]);
});
