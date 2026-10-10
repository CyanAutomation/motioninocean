import test from "node:test";
import assert from "node:assert/strict";
import {
  hydrateCameraSettingsForm,
  hydrateDiscoverySettingsForm,
} from "../../frontend/src/settings-form.ts";
import { asTestDouble } from "./test-doubles.ts";

interface TestControl {
  value: string;
  checked: boolean;
}

function createDependencies(controls: Record<string, TestControl>) {
  const sliderValues: string[] = [];
  return {
    dependencies: asTestDouble<Parameters<typeof hydrateCameraSettingsForm>[1]>({
      getValueControl: (id: string) => controls[id] || null,
      getCheckboxControl: (id: string) => controls[id] || null,
      updateSlider: (control: HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement) => {
        sliderValues.push(control.value);
      },
    }),
    sliderValues,
  };
}

test("renderCameraSettings hydrates numeric zero values without replacing them with defaults", () => {
  const controls = {
    "setting-resolution": { value: "", checked: false },
    "setting-fps": { value: "", checked: false },
    "setting-jpeg-quality": { value: "", checked: false },
    "setting-max-connections": { value: "", checked: false },
    "setting-max-frame-age": { value: "", checked: false },
  };
  const { dependencies, sliderValues } = createDependencies(controls);

  hydrateCameraSettingsForm(
    {
      fps: 0,
      jpeg_quality: 0,
      max_stream_connections: 0,
      max_frame_age_seconds: 0,
    },
    dependencies,
  );

  assert.equal(controls["setting-fps"].value, "0");
  assert.equal(controls["setting-jpeg-quality"].value, "0");
  assert.equal(controls["setting-max-connections"].value, "0");
  assert.equal(controls["setting-max-frame-age"].value, "0");
  assert.deepEqual(sliderValues, ["0", "0"]);
});

test("renderDiscoverySettings hydrates interval zero and boolean state", () => {
  const controls = {
    "setting-discovery-enabled": { value: "", checked: false },
    "setting-discovery-url": { value: "", checked: false },
    "setting-discovery-token": { value: "", checked: false },
    "setting-discovery-interval": { value: "", checked: false },
  };
  const { dependencies } = createDependencies(controls);

  hydrateDiscoverySettingsForm(
    {
      discovery_enabled: true,
      discovery_management_url: "http://hub:8001",
      discovery_token: "secret",
      discovery_interval_seconds: 0,
    },
    dependencies,
  );

  assert.equal(controls["setting-discovery-enabled"].checked, true);
  assert.equal(controls["setting-discovery-url"].value, "http://hub:8001");
  assert.equal(controls["setting-discovery-token"].value, "secret");
  assert.equal(controls["setting-discovery-interval"].value, "0");

  hydrateDiscoverySettingsForm({}, dependencies);
  assert.equal(controls["setting-discovery-enabled"].checked, false);
  assert.equal(controls["setting-discovery-interval"].value, "30");
});
