import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

function extractArrowFunction(source, functionName) {
  const pattern = new RegExp(
    `const ${functionName} = \\(\\) => \\{[\\s\\S]*?\\n  \\};`,
    "m",
  );
  const match = source.match(pattern);
  if (!match) {
    throw new Error(`${functionName}() definition not found`);
  }
  return match[0];
}

test("renderCameraSettings hydrates numeric 0 values without falling back", () => {
  const settingsJs = fs.readFileSync("pi_camera_in_docker/static/js/settings.js", "utf8");
  const renderCameraSettingsFn = extractArrowFunction(settingsJs, "renderCameraSettings");

  const elements = {
    "setting-fps": { value: "" },
    "setting-jpeg-quality": { value: "" },
    "setting-max-connections": { value: "" },
    "setting-max-frame-age": { value: "" },
  };
  const sliderValues = [];

  const context = {
    currentSettings: {
      camera: {
        fps: 0,
        jpeg_quality: 0,
        max_stream_connections: 0,
        max_frame_age_seconds: 0,
      },
    },
    document: {
      getElementById: (id) => elements[id] || null,
    },
    updateSliderDisplay: (slider) => {
      sliderValues.push(slider.value);
    },
  };

  vm.runInNewContext(`${renderCameraSettingsFn}; renderCameraSettings();`, context);

  assert.equal(elements["setting-fps"].value, 0);
  assert.equal(elements["setting-jpeg-quality"].value, 0);
  assert.equal(elements["setting-max-connections"].value, 0);
  assert.equal(elements["setting-max-frame-age"].value, 0);
  assert.deepEqual(sliderValues, [0, 0]);
});

test("renderDiscoverySettings hydrates interval 0 without default fallback", () => {
  const settingsJs = fs.readFileSync("pi_camera_in_docker/static/js/settings.js", "utf8");
  const renderDiscoverySettingsFn = extractArrowFunction(settingsJs, "renderDiscoverySettings");

  const intervalInput = { value: "" };

  const context = {
    currentSettings: {
      discovery: {
        discovery_interval_seconds: 0,
      },
    },
    document: {
      getElementById: (id) => {
        if (id === "setting-discovery-interval") {
          return intervalInput;
        }
        return null;
      },
    },
  };

  vm.runInNewContext(`${renderDiscoverySettingsFn}; renderDiscoverySettings();`, context);

  assert.equal(intervalInput.value, 0);
});
