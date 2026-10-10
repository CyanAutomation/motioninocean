import test from "node:test";
import assert from "node:assert/strict";
import { buildSettingsChangesSummaryModel } from "../../frontend/src/settings-summary.ts";

test("buildSettingsChangesSummaryModel maps overridden settings and restartability", () => {
  const model = buildSettingsChangesSummaryModel(
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

test("buildSettingsChangesSummaryModel ignores malformed overrides", () => {
  const model = buildSettingsChangesSummaryModel(
    {
      overridden: [
        { category: "camera", key: "resolution", value: "1280x720", env_value: "640x480" },
        { category: "camera", value: "invalid" },
        null,
        "invalid",
      ],
    },
    null,
  );

  assert.equal(model.items.length, 1);
  assert.equal(model.restartRequired, false);
});

test("buildSettingsChangesSummaryModel tolerates missing overridden payload", () => {
  const model = buildSettingsChangesSummaryModel({}, null);
  assert.equal(model.items.length, 0);
  assert.equal(model.restartRequired, false);
});
