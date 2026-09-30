export type SetupWizardStep = "environment" | "preset" | "review" | "generate";

export interface SetupWizardValues {
  piVersion: string;
  intent: string;
  preset: string;
  resolution: string;
  fps: string;
}

export interface SetupWizardRestoreOptions {
  steps: readonly SetupWizardStep[];
  currentStep: SetupWizardStep;
  expertMode: boolean;
  setValue: (id: string, value: unknown) => void;
  setChecked: (id: string, checked: boolean) => void;
  applyFields: (fields: Record<string, unknown>) => void;
}

export interface SetupWizardState {
  currentStep: SetupWizardStep;
  expertMode: boolean;
}

export interface DeviceDetectionPayload {
  video_devices?: string[];
  media_devices?: string[];
  dma_heap_devices?: string[];
  vchiq_device?: unknown;
}

export interface DeviceDetectionConfig {
  intent?: unknown;
}

export interface DeviceDetectionSummary {
  status: string;
  tone: "detected" | "warning" | "error";
  guidance: string;
  recommendations: string[];
  isManagementMode: boolean;
  videoCount: number;
  mediaCount: number;
  dmaCount: number;
  hasVchiq: boolean;
}

const WIZARD_STEPS: readonly SetupWizardStep[] = ["environment", "preset", "review", "generate"];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stringValue(value: unknown): string {
  return typeof value === "string" ? value : "";
}

/**
 * Validate a wizard step from the current form values.
 *
 * @param step - Wizard step to validate.
 * @param expertMode - Whether expert mode bypasses guided validation.
 * @param values - Current environment and configuration form values.
 * @returns True when the step can advance.
 */
export function validateSetupStep(
  step: string,
  expertMode: boolean,
  values: SetupWizardValues,
): boolean {
  if (expertMode) {
    return true;
  }
  if (step === "environment") {
    return Boolean(values.piVersion && values.intent);
  }
  if (step === "preset") {
    return Boolean(values.preset);
  }
  if (step === "review") {
    const fps = Number.parseInt(values.fps, 10);
    return /^\d+x\d+$/i.test(values.resolution) && Number.isInteger(fps) && fps >= 1 && fps <= 120;
  }
  return true;
}

/**
 * Recommend a setup preset from the selected Pi model and deployment intent.
 *
 * @param piVersion - Selected Raspberry Pi model.
 * @param intent - Selected deployment intent.
 * @returns A supported setup preset key.
 */
export function inferSetupPreset(piVersion: string, intent: string): string {
  if (piVersion === "pi3") {
    return "pi3_low_power";
  }
  if (piVersion === "pi5" || intent === "management") {
    return "pi5_high_quality";
  }
  return "custom";
}

/**
 * Restore persisted wizard values into supplied controls and form callbacks.
 *
 * @param storedValue - Parsed state from local storage.
 * @param options - Valid steps and callbacks for applying restored values.
 * @returns Restored wizard flags, or null when the saved value is malformed.
 */
export function restoreSetupWizardState(
  storedValue: unknown,
  options: SetupWizardRestoreOptions,
): SetupWizardState | null {
  if (!isRecord(storedValue)) {
    return null;
  }

  const environment = isRecord(storedValue.environment) ? storedValue.environment : {};
  options.setValue("env-pi-version", environment.piVersion ?? "");
  options.setValue("env-intent", environment.intent ?? "");
  options.setValue("env-mock-camera", environment.mockCamera ?? "false");

  if (storedValue.preset) {
    options.setValue("preset-select", storedValue.preset);
  }

  options.applyFields(isRecord(storedValue.fields) ? storedValue.fields : {});

  const expertMode = Boolean(storedValue.expertMode);
  options.setChecked("expert-mode-toggle", expertMode);
  const storedStep = stringValue(storedValue.currentStep);
  const currentStep = options.steps.includes(storedStep as SetupWizardStep)
    ? (storedStep as SetupWizardStep)
    : options.currentStep;

  return { currentStep, expertMode };
}

/**
 * Summarize detected camera devices and recommended setup guidance.
 *
 * @param devices - Device discovery response.
 * @param currentConfig - Current application configuration.
 * @param selectedIntent - Optional intent selected in the wizard.
 * @returns Device counts, status, guidance, and recommendations.
 */
export function createDeviceDetectionSummary(
  devices: DeviceDetectionPayload = {},
  currentConfig: DeviceDetectionConfig = {},
  selectedIntent = "",
): DeviceDetectionSummary {
  const videoCount = devices.video_devices?.length ?? 0;
  const mediaCount = devices.media_devices?.length ?? 0;
  const dmaCount = devices.dma_heap_devices?.length ?? 0;
  const hasVchiq = Boolean(devices.vchiq_device);
  const cameraSignals = [videoCount > 0, mediaCount > 0, hasVchiq].filter(Boolean).length;
  const modeIntent = selectedIntent || stringValue(currentConfig.intent);
  const isManagementMode = modeIntent === "management";
  const common = { isManagementMode, videoCount, mediaCount, dmaCount, hasVchiq };

  if (cameraSignals >= 2) {
    return {
      ...common,
      status: "Camera likely ready",
      tone: "detected",
      guidance: "Camera interfaces look available. You can proceed with real camera streaming.",
      recommendations: [
        "Enable the camera interface in raspi-config and reboot if the stream still fails.",
        "Keep /dev/vchiq and /dev/video* mounted into the container for hardware access.",
      ],
    };
  }

  if (cameraSignals === 0) {
    return {
      ...common,
      status: "No camera detected",
      tone: isManagementMode ? "warning" : "error",
      guidance: isManagementMode
        ? "Management mode can run without a physical camera, but streaming features will remain unavailable until hardware is attached."
        : "No camera interfaces were found. Check host device mounts and camera interface settings.",
      recommendations: [
        "Verify /dev/vchiq exists on the host and is mounted into the container.",
        "For local development without hardware, set MIO_MOCK_CAMERA=true.",
        "If using Raspberry Pi, enable Camera in raspi-config and reboot.",
      ],
    };
  }

  return {
    ...common,
    status: "Partial detection",
    tone: "warning",
    guidance: "Some camera signals were detected, but not all expected interfaces are present.",
    recommendations: [
      "Confirm /dev/vchiq and /dev/video* are both available to the container.",
      "Check camera ribbon seating and reboot if interfaces are intermittent.",
      "Use MIO_MOCK_CAMERA=true during development to continue testing setup flows.",
    ],
  };
}

export const setupWizardSteps = WIZARD_STEPS;
