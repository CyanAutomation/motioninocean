import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

function slice(source, startToken, endToken) {
  const start = source.indexOf(startToken);
  const end = source.indexOf(endToken, start);
  if (start === -1 || end === -1) {
    throw new Error(`Unable to slice from ${startToken} to ${endToken}`);
  }
  return source.slice(start, end).trim();
}

test("management template includes required webcam DOM ids used by management.js", () => {
  const template = fs.readFileSync("pi_camera_in_docker/templates/management.html", "utf8");
  const ids = new Set(Array.from(template.matchAll(/id="([^"]+)"/g), (match) => match[1]));
  const requiredIds = [
    "webcams-table-body",
    "webcam-form",
    "form-title",
    "cancel-edit-btn",
    "refresh-webcams-btn",
    "editing-webcam-id",
    "webcam-transport",
    "copy-diagnostic-report-btn",
  ];

  requiredIds.forEach((id) => {
    assert.equal(ids.has(id), true, `Missing id in management template: ${id}`);
  });
});

test("management init exits safely when required DOM ids are missing", async () => {
  const managementJs = fs.readFileSync("pi_camera_in_docker/static/js/management.js", "utf8");
  const initFn = slice(managementJs, "async function init()", "\n\ninit().catch");

  const feedbackCalls = [];
  const consoleErrors = [];
  const context = {
    getMissingRequiredElementIds: () => ["webcam-form"],
    console: {
      error: (message) => consoleErrors.push(message),
    },
    showFeedback: (...args) => feedbackCalls.push(args),
  };

  vm.runInNewContext(`${initFn};`, context);
  await context.init();

  assert.equal(feedbackCalls.length, 1);
  assert.deepEqual(feedbackCalls[0], [
    "Management UI failed to initialize due to missing page elements.",
    true,
  ]);
  assert.equal(consoleErrors.length, 1);
  assert.match(consoleErrors[0], /Missing required management UI element/);
});

