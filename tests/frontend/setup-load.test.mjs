import test from "node:test";
import assert from "node:assert/strict";
import { loadSetupTemplates } from "../../frontend/src/setup-load.ts";

function createCallbacks(overrides = {}) {
  const calls = [];
  return {
    calls,
    dependencies: {
      panelAvailable: true,
      fetchTemplates: async () => ({ current_config: { camera: {} } }),
      setLoading: (isLoading) => calls.push(["loading", isLoading]),
      applyTemplates: (data) => calls.push(["data", data]),
      isInitialized: () => false,
      initializeEventListeners: () => calls.push(["initialize"]),
      setWizardStep: () => calls.push(["step"]),
      setStatus: (status) => calls.push(["status", status]),
      onError: (error) => calls.push(["error", error.message]),
      logger: { error: (message, error) => calls.push(["log", message, error.message]) },
      ...overrides,
    },
  };
}

test("loadSetupTemplates applies fetched state and initializes the wizard", async () => {
  const { calls, dependencies } = createCallbacks();
  await loadSetupTemplates(dependencies);

  assert.deepEqual(
    calls.map(([name]) => name),
    ["loading", "data", "initialize", "step", "status", "loading"],
  );
  assert.deepEqual(calls[0], ["loading", true]);
  assert.deepEqual(calls.at(-1), ["loading", false]);
  assert.deepEqual(calls.at(-2), ["status", "ready"]);
});

test("loadSetupTemplates skips missing panels and already initialized listeners", async () => {
  let fetches = 0;
  const missingPanel = createCallbacks({
    panelAvailable: false,
    fetchTemplates: async () => {
      fetches += 1;
      return {};
    },
  });
  await loadSetupTemplates(missingPanel.dependencies);
  assert.equal(fetches, 0);
  assert.deepEqual(missingPanel.calls, []);

  const initialized = createCallbacks({ isInitialized: () => true });
  await loadSetupTemplates(initialized.dependencies);
  assert.equal(
    initialized.calls.some(([name]) => name === "initialize"),
    false,
  );
});

test("loadSetupTemplates reports failures and always hides the loading state", async () => {
  const { calls, dependencies } = createCallbacks({
    fetchTemplates: async () => {
      throw new Error("HTTP 503");
    },
  });
  await loadSetupTemplates(dependencies);

  assert.deepEqual(calls, [
    ["loading", true],
    ["log", "Failed to load setup tab:", "HTTP 503"],
    ["error", "HTTP 503"],
    ["status", "error"],
    ["loading", false],
  ]);
});
