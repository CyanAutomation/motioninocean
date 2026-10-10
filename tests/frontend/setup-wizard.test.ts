import test from "node:test";
import assert from "node:assert/strict";
import {
  createDeviceDetectionSummary,
  inferSetupPreset,
  restoreSetupWizardState,
  validateSetupStep,
} from "../../frontend/src/setup-wizard.ts";

test("setup step validation checks environment, preset, and camera settings", () => {
  const values = {
    piVersion: "pi5",
    intent: "webcam",
    preset: "custom",
    resolution: "1280x720",
    fps: "24",
  };

  assert.equal(validateSetupStep("environment", false, values), true);
  assert.equal(validateSetupStep("preset", false, values), true);
  assert.equal(validateSetupStep("review", false, values), true);
  assert.equal(validateSetupStep("review", false, { ...values, resolution: "1280x720p" }), false);
  assert.equal(validateSetupStep("review", true, { ...values, fps: "0" }), true);
});

test("setup preset selection follows Pi model and deployment intent", () => {
  assert.equal(inferSetupPreset("pi3", "webcam"), "pi3_low_power");
  assert.equal(inferSetupPreset("pi5", "webcam"), "pi5_high_quality");
  assert.equal(inferSetupPreset("pi4", "management"), "pi5_high_quality");
  assert.equal(inferSetupPreset("pi4", "webcam"), "custom");
});

test("stored wizard state restores controls and ignores unknown steps", () => {
  const values = new Map();
  let fields = {};
  const state = restoreSetupWizardState(
    {
      currentStep: "missing-step",
      expertMode: "yes",
      environment: { piVersion: "pi5", intent: "webcam", mockCamera: "true" },
      preset: "pi5_high_quality",
      fields: { resolution: "1280x720", fps: 24 },
    },
    {
      steps: ["environment", "preset", "review", "generate"],
      currentStep: "review",
      expertMode: false,
      setValue: (id, value) => values.set(id, String(value)),
      setChecked: (id, checked) => values.set(id, checked),
      applyFields: (config) => {
        fields = config;
      },
    },
  );

  assert.deepEqual(state, { currentStep: "review", expertMode: true });
  assert.equal(values.get("env-pi-version"), "pi5");
  assert.equal(values.get("env-intent"), "webcam");
  assert.equal(values.get("env-mock-camera"), "true");
  assert.equal(values.get("preset-select"), "pi5_high_quality");
  assert.equal(values.get("expert-mode-toggle"), true);
  assert.deepEqual(fields, { resolution: "1280x720", fps: 24 });
  assert.equal(
    restoreSetupWizardState(null, {
      steps: ["environment"],
      currentStep: "environment",
      expertMode: false,
      setValue: () => {},
      setChecked: () => {},
      applyFields: () => {},
    }),
    null,
  );
});

test("device summary permits management mode without camera hardware", () => {
  const summary = createDeviceDetectionSummary(
    { video_devices: [], media_devices: [], dma_heap_devices: [], vchiq_device: false },
    {},
    "management",
  );

  assert.equal(summary.status, "No camera detected");
  assert.equal(summary.tone, "warning");
  assert.equal(summary.isManagementMode, true);
  assert.match(summary.guidance, /can run without a physical camera/i);
  assert.equal(summary.videoCount, 0);
});
