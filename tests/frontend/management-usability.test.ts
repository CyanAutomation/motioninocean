import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const template = fs.readFileSync("pi_camera_in_docker/templates/management.html", "utf8");
const styles = fs.readFileSync("pi_camera_in_docker/static/css/ui-primitives.css", "utf8");
const managementStyles = fs.readFileSync("pi_camera_in_docker/static/css/management.css", "utf8");
const managementLogic = fs.readFileSync("frontend/src/management.ts", "utf8");

test("management dashboard uses one visible-label navigation across viewport sizes", () => {
  assert.equal((template.match(/<nav\b/g) || []).length, 1);
  assert.match(template, /id="management-view-nav"[^>]*class="[^"]*ui-sidebar/);
  for (const label of ["Overview", "Devices", "Discovered devices", "Settings"]) {
    assert.match(template, new RegExp(`>${label}<`));
  }
  assert.doesNotMatch(template, /management-side-rail|management-bottom-rail|rail-overview-btn|mobile-overview-btn/);
  assert.match(styles, /\.ui-sidebar__link\[aria-current="page"\]/);
  assert.match(styles, /@media\s*\(max-width:\s*56rem\)/);
});

test("each management view has a descriptive page header and one primary heading", () => {
  for (const [id, title] of [
    ["overview-title", "Overview"],
    ["devices-title", "Devices"],
    ["discovered-title", "Discovered devices"],
    ["settings-title", "Settings"],
  ]) {
    assert.match(template, new RegExp(`<h1[^>]*id="${id}"[^>]*>\\s*${title}\\s*</h1>`));
  }
  assert.equal((template.match(/class="ui-page-header"/g) || []).length, 4);
  assert.equal((template.match(/class="ui-page-header__description"/g) || []).length, 4);
});

test("registered webcams have an accessible search and status filter toolbar", () => {
  assert.match(template, /class="ui-toolbar"[^>]*aria-label="Webcam list filters"/);
  assert.match(template, /id="webcam-search"[^>]*type="search"/);
  assert.match(template, /for="webcam-search"/);
  assert.match(template, /id="webcam-status-filter"/);
  assert.match(template, /value="online"/);
  assert.match(template, /value="needs-attention"/);
  assert.match(template, /id="webcam-filter-summary"/);
  assert.match(managementLogic, /filterCollectionRows/);
});

test("management layout cards can shrink around their scrollable tables on mobile", () => {
  assert.match(managementStyles, /\.management-layout\s*>\s*\*\s*\{[^}]*min-inline-size:\s*0/s);
});

test("settings use grouped sections instead of incomplete tab controls", () => {
  assert.doesNotMatch(template, /data-settings-tab|settings-tab-row/);
  assert.equal((template.match(/class="ui-settings-group"/g) || []).length, 3);
  assert.match(template, /class="ui-settings-row"/);
  assert.match(template, /aria-describedby="settings-discovery-enabled-help"/);
  assert.match(template, /class="ui-settings-group__heading"/);
});

test("destructive management actions share a native confirmation dialog", () => {
  assert.match(template, /<dialog[^>]*id="utility-panel"/);
  assert.match(template, /<dialog[^>]*id="management-confirm-dialog"/);
  assert.match(template, /data-confirm-title/);
  assert.match(template, /data-confirm-message/);
  assert.match(template, /data-confirm-cancel[^>]*autofocus/);
  assert.match(template, /<button[^>]*value="confirm"[^>]*data-confirm-accept/);
  assert.match(managementLogic, /confirmInDialog/);
  assert.doesNotMatch(managementLogic, /window\.confirm\(/);
  assert.match(styles, /\.ui-dialog/);
});

test("shared UI primitives cover shell, headers, toolbars, settings rows, and statuses", () => {
  for (const primitive of [
    ".ui-app-shell",
    ".ui-page-header",
    ".ui-toolbar",
    ".ui-settings-group",
    ".ui-settings-row",
    ".ui-badge",
    ".ui-dialog",
  ]) {
    assert.ok(styles.includes(primitive), `Missing reusable UI primitive ${primitive}`);
  }
});
