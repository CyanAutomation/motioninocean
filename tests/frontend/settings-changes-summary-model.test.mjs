import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

function extractBuildSummaryModel(source) {
  const match = source.match(/function buildSettingsChangesSummaryModel\([^)]*\) \{[\s\S]*?\n^}/m);
  if (!match) {
    throw new Error("buildSettingsChangesSummaryModel() definition not found");
  }
  return match[0];
}

test("buildSettingsChangesSummaryModel maps overridden settings and restartability", () => {
  const settingsJs = fs.readFileSync("pi_camera_in_docker/static/js/settings.js", "utf8");
  const buildModelFn = extractBuildSummaryModel(settingsJs);

  const context = {};
  vm.runInNewContext(`${buildModelFn};`, context);

  const model = context.buildSettingsChangesSummaryModel(
    {
      overridden: [
        { category: "camera", key: "resolution", value: "1280x720", env_value: "640x480" },
        { category: "logging", key: "log_level", value: "DEBUG", env_value: "INFO" },
      ],
    },
    {
      camera: { properties: { resolution: { restartable: true } } },
      logging: { properties: { log_level: { restartable: false } } },
    },
  );

  assert.equal(model.items.length, 2);
  assert.equal(model.items[0].restartable, true);
  assert.equal(model.items[1].restartable, false);
  assert.equal(model.restartRequired, true);
});

test("buildSettingsChangesSummaryModel tolerates missing overridden payload", () => {
  const settingsJs = fs.readFileSync("pi_camera_in_docker/static/js/settings.js", "utf8");
  const buildModelFn = extractBuildSummaryModel(settingsJs);

  const context = {};
  vm.runInNewContext(`${buildModelFn};`, context);

  const model = context.buildSettingsChangesSummaryModel({}, null);
  assert.equal(model.items.length, 0);
  assert.equal(model.restartRequired, false);
});
