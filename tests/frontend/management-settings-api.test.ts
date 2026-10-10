import test from "node:test";
import assert from "node:assert/strict";
import {
  describeManagementApiError,
  fetchManagementSettings,
  saveManagementSettings,
} from "../../frontend/src/management-settings-api.ts";

test("describeManagementApiError explains known discovery and webcam auth failures", () => {
  assert.match(
    describeManagementApiError({ error: { code: "DISCOVERY_PRIVATE_IP_BLOCKED", details: {} } }),
    /private-IP policy/,
  );
  assert.match(
    describeManagementApiError({ code: "WEBCAM_UNAUTHORIZED" }),
    /match WEBCAM_CONTROL_PLANE_AUTH_TOKEN/,
  );
  assert.equal(
    describeManagementApiError({
      code: "DISCOVERY_PRIVATE_IP_BLOCKED",
      details: { remediation: "Use internal routing." },
    }),
    "Discovery registration blocked by private-IP policy. Use internal routing.",
  );
});

test("describeManagementApiError preserves nested messages and handles malformed payloads", () => {
  assert.equal(
    describeManagementApiError({ error: { code: "SSRF_BLOCKED" } }),
    "Private-IP policy blocked this target. Use a docker network hostname, or explicitly enable MIO_ALLOW_PRIVATE_IPS=true on management for trusted internal networks.",
  );
  assert.equal(
    describeManagementApiError({ error: { message: "Nested failure" } }),
    "Nested failure",
  );
  assert.equal(describeManagementApiError({ message: "Top-level failure" }), "Top-level failure");
  assert.equal(describeManagementApiError(null), "Request failed.");
  assert.equal(describeManagementApiError("bad payload"), "Request failed.");
});

test("fetchManagementSettings loads settings and optional override data concurrently", async () => {
  const requested: string[] = [];
  const fetcher: Parameters<typeof fetchManagementSettings>[0] = async (path) => {
    requested.push(path);
    return {
      ok: true,
      status: 200,
      json: async () => (path.endsWith("/changes") ? { overridden: [] } : { discovery: {} }),
    };
  };

  const result = await fetchManagementSettings(fetcher);
  assert.deepEqual(requested, ["/api/v1/settings", "/api/v1/settings/changes"]);
  assert.deepEqual(result.settings, { discovery: {} });
  assert.deepEqual(result.changes, { overridden: [] });
});

test("fetchManagementSettings rejects a failed settings response and tolerates failed overrides", async () => {
  await assert.rejects(
    fetchManagementSettings(async () => ({ ok: false, status: 500, json: async () => ({}) })),
    /Could not load settings/,
  );

  const result = await fetchManagementSettings(async (path) => ({
    ok: !path.endsWith("/changes"),
    status: path.endsWith("/changes") ? 503 : 200,
    json: async () => ({ discovery: { discovery_enabled: true } }),
  }));
  assert.equal(result.changes, undefined);
});

test("saveManagementSettings distinguishes restart, success, server failure, and network failure", async () => {
  const patch = { discovery: { discovery_enabled: true } };
  const createResponse = (status: number, payload: unknown) => ({
    status,
    ok: status >= 200 && status < 300,
    json: async (): Promise<unknown> => payload,
  });

  assert.deepEqual(
    await saveManagementSettings(
      async () => createResponse(422, { modified_on_restart: ["port"] }),
      patch,
    ),
    { kind: "restart-required", modifiedOnRestart: ["port"] },
  );
  assert.deepEqual(await saveManagementSettings(async () => createResponse(200, {}), patch), {
    kind: "saved",
  });
  assert.deepEqual(
    await saveManagementSettings(async () => createResponse(403, { message: "Denied" }), patch),
    { kind: "failure", message: "Denied" },
  );
  assert.deepEqual(
    await saveManagementSettings(async () => {
      throw new Error("offline");
    }, patch),
    { kind: "failure", message: "offline" },
  );
});
