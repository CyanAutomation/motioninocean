import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

test("frame staleness guidance remains part of the documented settings UI", () => {
  // Traceability: docs/product/PRD-backend.md, readiness depends on frame freshness.
  const template = fs.readFileSync("pi_camera_in_docker/templates/index.html", "utf8");

  assert.match(template, /Maximum Frame Staleness \(seconds\)/);
  assert.match(template, /Freshness threshold for the latest captured frame/);
  assert.match(template, /Readiness and health checks report frames older than this as stale/);
});
