import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { REQUIRED_MANAGEMENT_ELEMENT_IDS } from "../../frontend/src/management-dom.ts";
import { asTestDouble } from "./test-doubles.ts";

function slice(source: string, startToken: string, endToken: string): string {
  const start = source.indexOf(startToken);
  const end = source.indexOf(endToken, start);
  if (start === -1 || end === -1) {
    throw new Error(`Unable to slice from ${startToken} to ${endToken}`);
  }
  return source.slice(start, end).trim();
}

test("management template includes every DOM element required by the dashboard", () => {
  // Traceability: docs/product/PRD-frontend.md, Management UI.
  const template = fs.readFileSync("pi_camera_in_docker/templates/management.html", "utf8");
  const ids = new Set(Array.from(template.matchAll(/id="([^"]+)"/g), (match) => match[1]));

  REQUIRED_MANAGEMENT_ELEMENT_IDS.forEach((id) => {
    assert.equal(ids.has(id), true, `Missing id in management template: ${id}`);
  });
});

test("management init exits safely when required DOM ids are missing", async () => {
  const managementJs = fs.readFileSync("frontend/src/management.ts", "utf8");
  const initFn = slice(managementJs, "async function init()", "\n\ninit().catch");

  const feedbackCalls: unknown[][] = [];
  const consoleErrors: string[] = [];
  const context = {
    getMissingRequiredElementIds: () => ["webcam-form"],
    console: {
      error: (message: string) => {
        consoleErrors.push(message);
      },
    },
    showFeedback: (message: string, isError = false) => {
      feedbackCalls.push([message, isError]);
    },
  };

  vm.runInNewContext(`${initFn};`, context);
  const evaluatedContext = asTestDouble<typeof context & { init(): Promise<void> }>(context);
  await evaluatedContext.init();

  assert.equal(feedbackCalls.length, 1);
  assert.deepEqual(feedbackCalls[0], [
    "Management UI failed to initialize due to missing page elements.",
    true,
  ]);
  assert.equal(consoleErrors.length, 1);
  assert.match(consoleErrors[0], /Missing required management UI element/);
});
