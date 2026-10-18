import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  REQUIRED_MANAGEMENT_ELEMENT_IDS,
  validateManagementDom,
} from "../../frontend/src/management-dom.ts";

test("management template includes every DOM element required by the dashboard", () => {
  // Traceability: docs/product/PRD-frontend.md, Management UI.
  const template = fs.readFileSync("pi_camera_in_docker/templates/management.html", "utf8");
  const ids = new Set(Array.from(template.matchAll(/id="([^"]+)"/g), (match) => match[1]));

  REQUIRED_MANAGEMENT_ELEMENT_IDS.forEach((id) => {
    assert.equal(ids.has(id), true, `Missing id in management template: ${id}`);
  });
});

test("management initialization reports missing required DOM elements and stops", () => {
  const feedbackCalls: Array<[string, boolean | undefined]> = [];
  const consoleErrors: string[] = [];
  const document = {
    getElementById: (id: string) => (id === "webcam-form" ? null : ({} as HTMLElement)),
  } as Pick<Document, "getElementById">;
  const logger = { error: (message: string) => consoleErrors.push(message) };

  const isReady = validateManagementDom(document, logger, (message, isError) => {
    feedbackCalls.push([message, isError]);
  });

  assert.equal(isReady, false);
  assert.deepEqual(feedbackCalls, [
    ["Management UI failed to initialize due to missing page elements.", true],
  ]);
  assert.equal(consoleErrors.length, 1);
  assert.match(consoleErrors[0]!, /Missing required management UI element\(s\): webcam-form/);
});

test("management initialization can proceed when all required DOM elements exist", () => {
  const document = {
    getElementById: () => ({} as HTMLElement),
  } as Pick<Document, "getElementById">;
  const logger = { error: () => assert.fail("Unexpected management initialization error") };
  const feedback = () => assert.fail("Unexpected management initialization feedback");

  assert.equal(validateManagementDom(document, logger, feedback), true);
});
