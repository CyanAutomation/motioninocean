import test from "node:test";
import assert from "node:assert/strict";
import { runConfigUpdate } from "../../frontend/src/config-update.ts";

function createState(overrides = {}) {
  return {
    configInFlight: false,
    configInitialLoadPending: false,
    configLoadingDelayTimer: null,
    configLoadingVisible: false,
    ...overrides,
  };
}

function createDependencies(overrides = {}) {
  const calls = { rendered: [], errors: [], warnings: [], logged: [], cleared: 0 };
  const classes = new Set(["hidden"]);
  const dependencies = {
    isActive: true,
    loadingElement: {
      classList: { add: (name) => classes.add(name), remove: (name) => classes.delete(name) },
    },
    fetchConfig: async () => ({ stream: { fps: 24 } }),
    renderConfig: (data) => calls.rendered.push(data),
    clearConfigDisplay: () => {
      calls.cleared += 1;
    },
    showConfigError: (message) => calls.errors.push(message),
    logger: {
      warn: (message) => calls.warnings.push(message),
      error: (...args) => calls.logged.push(args),
    },
    classes,
    calls,
    ...overrides,
  };
  return dependencies;
}

test("runConfigUpdate skips inactive and already-running refreshes", async () => {
  const dependencies = createDependencies({ isActive: false });
  await runConfigUpdate(createState(), dependencies);
  await runConfigUpdate(createState({ configInFlight: true }), createDependencies());
  assert.deepEqual(dependencies.calls.rendered, []);
});

test("runConfigUpdate renders success, timestamps it, and cleans up delayed loading", async () => {
  let resolveConfig;
  let showLoading;
  const cancelledTimers = [];
  const state = createState({ configInitialLoadPending: true });
  const dependencies = createDependencies({
    schedule: (callback) => {
      showLoading = callback;
      return 1;
    },
    cancel: (timer) => cancelledTimers.push(timer),
    fetchConfig: () =>
      new Promise((resolve) => {
        resolveConfig = resolve;
      }),
  });
  const update = runConfigUpdate(state, dependencies);

  assert.equal(state.configInFlight, true);
  assert.equal(state.configLoadingDelayTimer, 1);
  showLoading();
  assert.equal(state.configLoadingVisible, true);
  assert.equal(dependencies.classes.has("hidden"), false);
  resolveConfig({ stream: { fps: 30 } });
  await update;

  assert.deepEqual(dependencies.calls.rendered, [{ stream: { fps: 30 } }]);
  assert.ok(state.lastConfigUpdate instanceof Date);
  assert.equal(state.configInFlight, false);
  assert.equal(state.configInitialLoadPending, false);
  assert.equal(state.configLoadingDelayTimer, null);
  assert.equal(state.configLoadingVisible, false);
  assert.equal(dependencies.classes.has("hidden"), true);
  assert.deepEqual(cancelledTimers, [1]);
});

test("runConfigUpdate reports timeouts without clearing the last display", async () => {
  const error = new Error("aborted");
  error.name = "AbortError";
  const dependencies = createDependencies({
    fetchConfig: async () => {
      throw error;
    },
  });
  const state = createState();

  await runConfigUpdate(state, dependencies);
  assert.deepEqual(dependencies.calls.warnings, ["Config request timed out, will retry."]);
  assert.deepEqual(dependencies.calls.errors, [
    "Configuration request timed out. Will retry automatically.",
  ]);
  assert.equal(dependencies.calls.cleared, 0);
  assert.equal(state.configInFlight, false);
});

test("runConfigUpdate clears stale values and reports ordinary failures", async () => {
  const dependencies = createDependencies({
    fetchConfig: async () => {
      throw new Error("offline");
    },
  });
  const state = createState();

  await runConfigUpdate(state, dependencies);
  assert.equal(dependencies.calls.cleared, 1);
  assert.deepEqual(dependencies.calls.errors, ["Failed to load configuration: offline"]);
  assert.equal(state.configInFlight, false);
});
