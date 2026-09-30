import test from "node:test";
import assert from "node:assert/strict";
import {
  buildManagementSettingsPatch,
  hydrateManagementSettingsForm,
} from "../../frontend/src/management-settings-view.ts";

test("hydrateManagementSettingsForm fills supported controls and defaults", () => {
  const controls = {
    enabled: { value: "", checked: false },
    url: { value: "", checked: false },
    token: { value: "", checked: false },
    interval: { value: "", checked: false },
  };

  hydrateManagementSettingsForm(
    {
      discovery_enabled: true,
      discovery_management_url: "http://hub:8001",
      discovery_token: "secret",
      discovery_interval_seconds: 0,
    },
    controls,
  );

  assert.deepEqual(controls, {
    enabled: { value: "", checked: true },
    url: { value: "http://hub:8001", checked: false },
    token: { value: "secret", checked: false },
    interval: { value: "0", checked: false },
  });

  hydrateManagementSettingsForm({}, controls);
  assert.deepEqual(controls, {
    enabled: { value: "", checked: false },
    url: { value: "", checked: false },
    token: { value: "", checked: false },
    interval: { value: "30", checked: false },
  });
});

test("buildManagementSettingsPatch normalizes input values and rejects missing controls", () => {
  assert.deepEqual(
    buildManagementSettingsPatch({
      enabled: { value: "", checked: true },
      url: { value: " http://hub:8001 ", checked: false },
      token: { value: " token ", checked: false },
      interval: { value: "45", checked: false },
    }),
    {
      discovery: {
        discovery_enabled: true,
        discovery_management_url: "http://hub:8001",
        discovery_token: "token",
        discovery_interval_seconds: 45,
      },
    },
  );
  assert.equal(
    buildManagementSettingsPatch({ enabled: null, url: {}, token: {}, interval: {} }),
    null,
  );
  assert.equal(
    buildManagementSettingsPatch({
      enabled: { value: "", checked: false },
      url: {},
      token: {},
      interval: {},
    }),
    null,
  );
});
