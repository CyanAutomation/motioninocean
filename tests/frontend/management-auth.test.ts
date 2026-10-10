import test from "node:test";
import assert from "node:assert/strict";
import { createManagementBearerTokenSession } from "../../frontend/src/management-auth.ts";

test("management bearer tokens stay in session memory and clear legacy browser storage", () => {
  const legacyStorage = new Map([["management.apiToken", "persisted-token"]]);
  const storageCalls: Array<[string, string]> = [];
  const session = createManagementBearerTokenSession(() => ({
    removeItem(key: string) {
      storageCalls.push(["removeItem", key]);
      legacyStorage.delete(key);
    },
  }));

  assert.deepEqual(storageCalls, [["removeItem", "management.apiToken"]]);
  assert.equal(legacyStorage.has("management.apiToken"), false);
  assert.equal(session.getToken(), "");

  assert.equal(session.setToken("  session-token  "), "session-token");
  assert.equal(session.getToken(), "session-token");
  assert.equal(session.setToken(""), "");
  assert.equal(session.getToken(), "");

  assert.deepEqual(storageCalls, [["removeItem", "management.apiToken"]]);
});

test("management bearer token session works when browser storage is unavailable", () => {
  const session = createManagementBearerTokenSession(() => {
    throw new Error("Storage access is unavailable");
  });

  assert.equal(session.setToken("session-token"), "session-token");
  assert.equal(session.getToken(), "session-token");
});
