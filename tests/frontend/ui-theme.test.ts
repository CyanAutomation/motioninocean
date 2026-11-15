import test from "node:test";
import assert from "node:assert/strict";

import { createThemeController, resolveThemePreference } from "../../frontend/src/ui-theme.ts";

class FakeColorPreference {
  listeners: Array<(matches: boolean) => void> = [];

  constructor(public matches: boolean) {}

  onChange(listener: (matches: boolean) => void): void {
    this.listeners.push(listener);
  }

  setMatches(matches: boolean): void {
    this.matches = matches;
    for (const listener of this.listeners) listener(matches);
  }
}

function createThemeHarness(options: {
  storedTheme?: string | null;
  systemDark?: boolean;
  followSystemPreference?: boolean;
  storageThrows?: boolean;
} = {}) {
  const attributes: Record<string, string> = {};
  const writes: Array<[string, string]> = [];
  const appliedThemes: string[] = [];
  const colorPreference = new FakeColorPreference(options.systemDark ?? false);
  const root = {
    setAttribute(name: string, value: string) {
      attributes[name] = value;
    },
  };
  const storage = {
    getItem() {
      if (options.storageThrows) throw new Error("Storage unavailable");
      return options.storedTheme ?? null;
    },
    setItem(key: string, value: string) {
      if (options.storageThrows) throw new Error("Storage unavailable");
      writes.push([key, value]);
    },
  };
  const controller = createThemeController({
    storageKey: "camera.theme",
    getRoot: () => root,
    getStorage: () => storage,
    getColorPreference: () => colorPreference,
    followSystemPreference: options.followSystemPreference,
    onThemeChange: (theme) => appliedThemes.push(theme),
  });

  return { controller, attributes, writes, appliedThemes, colorPreference };
}

test("theme preference keeps valid saved choices and otherwise uses the system default", () => {
  assert.equal(resolveThemePreference("dark", false), "dark");
  assert.equal(resolveThemePreference("light", true), "light");
  assert.equal(resolveThemePreference(null, true), "dark");
  assert.equal(resolveThemePreference("invalid", false), "light");
});

test("applying a theme normalizes it, updates the root, notifies the page, and persists it", () => {
  const harness = createThemeHarness();

  harness.controller.applyTheme("dark");
  harness.controller.applyTheme("invalid");

  assert.equal(harness.attributes["data-theme"], "light");
  assert.deepEqual(harness.appliedThemes, ["dark", "light"]);
  assert.deepEqual(harness.writes, [
    ["camera.theme", "dark"],
    ["camera.theme", "light"],
  ]);
});

test("initialization respects a saved theme and does not overwrite that preference", () => {
  const harness = createThemeHarness({ storedTheme: "light", systemDark: true });

  harness.controller.initializeTheme();

  assert.equal(harness.attributes["data-theme"], "light");
  assert.deepEqual(harness.appliedThemes, ["light"]);
  assert.deepEqual(harness.writes, []);
  assert.equal(harness.colorPreference.listeners.length, 0);
});

test("system theme changes apply until the user explicitly selects a theme", () => {
  const harness = createThemeHarness({ followSystemPreference: true, systemDark: true });

  harness.controller.initializeTheme();
  harness.colorPreference.setMatches(false);
  harness.controller.applyTheme("dark");
  harness.colorPreference.setMatches(false);

  assert.deepEqual(harness.appliedThemes, ["dark", "light", "dark"]);
  assert.deepEqual(harness.writes, [["camera.theme", "dark"]]);
  assert.equal(harness.attributes["data-theme"], "dark");
});

test("system preference can be disabled and storage failures are ignored", () => {
  const appHarness = createThemeHarness({ followSystemPreference: false, systemDark: true });
  appHarness.controller.initializeTheme();
  assert.equal(appHarness.attributes["data-theme"], "light");
  assert.equal(appHarness.colorPreference.listeners.length, 0);

  const unavailableStorage = createThemeHarness({ storageThrows: true, systemDark: true });
  unavailableStorage.controller.initializeTheme();
  unavailableStorage.controller.applyTheme("dark");
  assert.equal(unavailableStorage.attributes["data-theme"], "dark");
  assert.deepEqual(unavailableStorage.writes, []);
});
