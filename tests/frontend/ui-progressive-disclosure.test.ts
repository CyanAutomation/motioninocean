import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

test("webcam stream keeps status prominent and defers secondary metrics", () => {
  const template = fs.readFileSync("pi_camera_in_docker/templates/index.html", "utf8");
  const detailsStart = template.indexOf('id="stats-panel"');
  const detailsEnd = template.indexOf("</details>", detailsStart);
  const detailsMarkup = template.slice(detailsStart, detailsEnd);

  assert.match(template, /id="chip-connected"/);
  assert.match(template, /id="chip-stale"/);
  assert.match(template, /id="chip-inactive"/);
  assert.match(detailsMarkup, /<summary class="stream-details__summary">/);
  assert.match(detailsMarkup, /id="chip-fps"/);
  assert.doesNotMatch(detailsMarkup, /id="vc-refresh-btn"|id="vc-fullscreen-btn"/);
  assert.doesNotMatch(template, /id="refresh-stream-header-btn"/);
});

test("configuration details collapse technical groups while health remains visible in the summary", () => {
  const template = fs.readFileSync("pi_camera_in_docker/templates/index.html", "utf8");

  assert.match(template, /<details class="config-group editable-section ui-card" open>/);
  assert.match(template, /<details class="config-group readonly-section ui-card">/);
  assert.match(template, /config-summary-health[\s\S]*id="config-health-overall"/);
  assert.equal((template.match(/id="config-health-overall"/g) || []).length, 1);
});

test("runtime settings expose keyboard disclosure state and defer advanced sections", () => {
  const template = fs.readFileSync("pi_camera_in_docker/templates/index.html", "utf8");

  assert.match(
    template,
    /data-section="camera"[\s\S]*?aria-expanded="true"[\s\S]*?aria-controls="settings-camera-content"/,
  );
  assert.match(
    template,
    /data-section="logging"[\s\S]*?aria-expanded="false"[\s\S]*?aria-controls="settings-logging-content"/,
  );
  assert.match(template, /class="settings-section-content collapsed"[\s\S]*?inert/);
});

test("management dashboard consolidates auth entry and keeps optional node fields behind details", () => {
  const template = fs.readFileSync("pi_camera_in_docker/templates/management.html", "utf8");

  assert.match(template, /<details id="management-token-disclosure"/);
  assert.equal((template.match(/id="management-api-token"/g) || []).length, 1);
  assert.doesNotMatch(template, /settings-management-api-token/);
  assert.match(template, /<details id="webcam-advanced-options"/);
  assert.match(template, /id="show-management-token-btn"/);
  assert.match(template, /id="webcams-table-body"/);
  assert.match(template, /<th>Node<\/th>[\s\S]*?<th>Status<\/th>[\s\S]*?<th>Stream<\/th>[\s\S]*?<th>Actions<\/th>/);
});

test("management activity and runtime overrides start collapsed while attention stays visible", () => {
  const template = fs.readFileSync("pi_camera_in_docker/templates/management.html", "utf8");

  assert.match(template, /<details class="overview-panel ui-card overview-activity-panel">/);
  assert.match(template, /<h3>Needs attention<\/h3>/);
  assert.match(template, /<details class="runtime-overrides">/);
  assert.match(template, /<details class="ui-card discovered-panel discovered-notes-panel">/);
  assert.match(template, /Select a device from the list to enable these actions/);
});
