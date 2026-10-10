import test from "node:test";
import assert from "node:assert/strict";
import { saveSettingsPatch } from "../../frontend/src/settings-api.ts";

function response(status, body) {
  return {
    status,
    json: async () => body,
  };
}

test("saveSettingsPatch classifies saved and restart-required responses", async () => {
  const patch = { camera: { fps: 24 } };
  const fetcher = async (_url, options) => {
    assert.equal(options.method, "PATCH");
    assert.deepEqual(JSON.parse(options.body), patch);
    return response(200, { settings: { camera: { fps: 24 } } });
  };

  assert.deepEqual(await saveSettingsPatch(fetcher, patch), {
    kind: "saved",
    settings: { camera: { fps: 24 } },
  });

  assert.deepEqual(
    await saveSettingsPatch(
      async () =>
        response(422, {
          settings: { camera: { resolution: "1280x720" } },
          modified_on_restart: ["camera.resolution"],
        }),
      patch,
    ),
    {
      kind: "restart-required",
      settings: { camera: { resolution: "1280x720" } },
      modifiedOnRestart: ["camera.resolution"],
    },
  );
});

test("saveSettingsPatch formats validation errors and rejects unexpected statuses", async () => {
  assert.deepEqual(
    await saveSettingsPatch(
      async () =>
        response(400, {
          validation_errors: { "camera.fps": "must be positive", resolution: "unsupported" },
        }),
      {},
    ),
    { kind: "validation-error", message: "camera.fps: must be positive\nresolution: unsupported" },
  );
  await assert.rejects(
    saveSettingsPatch(async () => response(503, {}), {}),
    /HTTP 503/,
  );
  await assert.rejects(
    saveSettingsPatch(async () => {
      throw new Error("offline");
    }, {}),
    /offline/,
  );
});

test("saveSettingsPatch handles malformed JSON for each supported response", async () => {
  const malformedResponse = (status) => ({
    status,
    json: async () => {
      throw new SyntaxError("Unexpected token");
    },
  });

  await assert.rejects(
    saveSettingsPatch(async () => malformedResponse(200), {}),
    /Failed to parse successful response/,
  );
  await assert.rejects(
    saveSettingsPatch(async () => malformedResponse(422), {}),
    /Failed to parse restart-required response/,
  );
  assert.deepEqual(await saveSettingsPatch(async () => malformedResponse(400), {}), {
    kind: "validation-error",
    message: "Validation failed but could not parse error details",
  });
});
