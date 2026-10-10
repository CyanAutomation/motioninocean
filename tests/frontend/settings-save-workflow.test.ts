import test from "node:test";
import assert from "node:assert/strict";
import {
  runSettingsSaveWorkflow,
  type SettingsSaveWorkflowDependencies,
} from "../../frontend/src/settings-save-workflow.ts";

type TestSettings = { camera: { fps: number } };
type TestPatch = { camera: { fps: number } };
type TestDependencies = SettingsSaveWorkflowDependencies<TestSettings, TestPatch>;

function createDependencies(overrides: Partial<TestDependencies> = {}) {
  const calls: unknown[][] = [];
  const dependencies: TestDependencies = {
    isDirty: () => true,
    dirtyFieldCount: () => 1,
    getPendingChanges: () => [{ category: "camera", property: "fps", oldValue: 20, newValue: 24 }],
    confirm: async () => true,
    buildPatch: (_changes, key) => ({ camera: { fps: key === "newValue" ? 24 : 20 } }),
    getSaveButton: () => ({ disabled: false }),
    save: async () => ({ kind: "saved", settings: { camera: { fps: 24 } } }),
    setCurrentSettings: (settings) => calls.push(["settings", settings]),
    clearDirtyFields: () => calls.push(["clear-dirty"]),
    setUndoState: (snapshot, changes) => calls.push(["undo", snapshot, changes]),
    updateSaveButton: () => calls.push(["update-button"]),
    refreshChangesSummary: async () => {
      calls.push(["refresh-summary"]);
    },
    showWarning: (message, metadata) => calls.push(["warning", message, metadata]),
    showError: (message, metadata) => calls.push(["error", message, metadata]),
    showSuccess: (message, metadata) => calls.push(["success", message, metadata]),
    logError: (error) => calls.push(["log-error", error]),
    describeError: (error) => (error instanceof Error ? error.message : String(error)),
  };
  return { dependencies: { ...dependencies, ...overrides }, calls };
}

test("runSettingsSaveWorkflow stops for clean or empty changes", async () => {
  const clean = createDependencies({ isDirty: () => false });
  await runSettingsSaveWorkflow(clean.dependencies);
  assert.equal(clean.calls[0][1], "No changes to save");

  const empty = createDependencies({ getPendingChanges: () => [] });
  await runSettingsSaveWorkflow(empty.dependencies);
  assert.equal(empty.calls[0][1], "No valid settings changes found");
});

test("runSettingsSaveWorkflow stops when save confirmation is declined", async () => {
  const { dependencies, calls } = createDependencies({ confirm: async () => false });
  await runSettingsSaveWorkflow(dependencies);
  assert.deepEqual(calls, []);
});

test("runSettingsSaveWorkflow saves settings and records undo state", async () => {
  const { dependencies, calls } = createDependencies();
  await runSettingsSaveWorkflow(dependencies);

  assert.deepEqual(
    calls.map(([name]) => name),
    ["settings", "clear-dirty", "undo", "update-button", "refresh-summary", "success"],
  );
  assert.deepEqual(calls.at(-1), ["success", "Settings saved successfully!", { outcome: "saved" }]);
});

test("runSettingsSaveWorkflow reports validation errors and re-enables save", async () => {
  const button = { disabled: false };
  const { dependencies, calls } = createDependencies({
    getSaveButton: () => button,
    save: async () => ({ kind: "validation-error", message: "camera.fps: must be positive" }),
  });
  await runSettingsSaveWorkflow(dependencies);

  assert.equal(button.disabled, false);
  assert.deepEqual(calls[0], [
    "error",
    "Validation error:\ncamera.fps: must be positive",
    { outcome: "failed", details: "camera.fps: must be positive" },
  ]);
});

test("runSettingsSaveWorkflow reports restart-required changes", async () => {
  const { dependencies, calls } = createDependencies({
    save: async () => ({
      kind: "restart-required",
      settings: { camera: { fps: 24 } },
      modifiedOnRestart: ["camera.resolution"],
    }),
  });
  await runSettingsSaveWorkflow(dependencies);
  assert.deepEqual(calls.at(-1), [
    "warning",
    "Settings saved! Some changes require server restart:\ncamera.resolution",
    { outcome: "restart-required", details: "camera.resolution" },
  ]);
});

test("runSettingsSaveWorkflow safely formats non-string restart details", async () => {
  const { dependencies, calls } = createDependencies({
    save: async () => ({
      kind: "restart-required",
      settings: { camera: { fps: 24 } },
      modifiedOnRestart: ["camera.resolution", 24, Symbol("camera")],
    }),
  });
  await runSettingsSaveWorkflow(dependencies);
  assert.deepEqual(calls.at(-1), [
    "warning",
    "Settings saved! Some changes require server restart:\ncamera.resolution\n24\nSymbol(camera)",
    { outcome: "restart-required", details: "camera.resolution\n24\nSymbol(camera)" },
  ]);
});

test("runSettingsSaveWorkflow supplies default restart details when none are returned", async () => {
  const { dependencies, calls } = createDependencies({
    save: async () => ({ kind: "restart-required", settings: { camera: { fps: 24 } } }),
  });
  await runSettingsSaveWorkflow(dependencies);
  assert.deepEqual(calls.at(-1), [
    "warning",
    "Settings saved! Some changes require server restart:\nServer restart required to apply some settings.",
    {
      outcome: "restart-required",
      details: "Server restart required to apply some settings.",
    },
  ]);
});

test("runSettingsSaveWorkflow reports save failures and re-enables save", async () => {
  const button = { disabled: false };
  const failure = new Error("offline");
  const { dependencies, calls } = createDependencies({
    getSaveButton: () => button,
    save: async () => {
      throw failure;
    },
  });
  await runSettingsSaveWorkflow(dependencies);

  assert.equal(button.disabled, false);
  assert.deepEqual(calls, [
    ["log-error", failure],
    ["error", "Failed to save settings: offline", { outcome: "failed", details: "offline" }],
  ]);
});
