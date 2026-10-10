import test from "node:test";
import assert from "node:assert/strict";
import { generateSetupConfiguration } from "../../frontend/src/setup-generation.ts";

function makeResponse(status: number, payload: unknown): Pick<Response, "ok" | "json"> {
  return {
    ok: status >= 200 && status < 300,
    json: async () => payload,
  };
}

test("generateSetupConfiguration validates before generating and returns generated contents", async () => {
  const calls: Array<{ path: string; options: { body: string } }> = [];
  const fetcher: NonNullable<Parameters<typeof generateSetupConfiguration>[1]> = async (
    path,
    options,
  ) => {
    calls.push({ path, options });
    return path.endsWith("/validate")
      ? makeResponse(200, { valid: true })
      : makeResponse(200, { docker_compose_yaml: "services: {}", env_content: "FPS=24" });
  };
  const config = { camera: { fps: 24 } };

  const result = await generateSetupConfiguration(config, fetcher);

  assert.deepEqual(result, {
    kind: "generated",
    dockerComposeYaml: "services: {}",
    envContent: "FPS=24",
  });
  assert.deepEqual(
    calls.map(({ path }) => path),
    ["/api/setup/validate", "/api/setup/generate"],
  );
  assert.deepEqual(JSON.parse(calls[0].options.body), config);
});

test("generateSetupConfiguration stops and returns validation errors", async () => {
  const calls: string[] = [];
  const result = await generateSetupConfiguration({}, async (path) => {
    calls.push(path);
    return makeResponse(200, { valid: false, errors: ["missing camera", "invalid FPS"] });
  });

  assert.deepEqual(result, { kind: "validation-error", errors: ["missing camera", "invalid FPS"] });
  assert.deepEqual(calls, ["/api/setup/validate"]);
});

test("generateSetupConfiguration reports validation and generation HTTP errors", async () => {
  await assert.rejects(
    generateSetupConfiguration({}, async () =>
      makeResponse(400, { error: { message: "Bad config" } }),
    ),
    /Bad config/,
  );
  await assert.rejects(
    generateSetupConfiguration({}, async (path) =>
      path.endsWith("/validate")
        ? makeResponse(200, { valid: true })
        : makeResponse(503, { error: { message: "Generator offline" } }),
    ),
    /Generator offline/,
  );
});
