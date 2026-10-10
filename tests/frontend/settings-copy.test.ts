import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

test("frame staleness setting explains its readiness and health semantics", () => {
  const template = fs.readFileSync("pi_camera_in_docker/templates/index.html", "utf8");

  assert.match(template, /Maximum Frame Staleness \(seconds\)/);
  assert.match(template, /Freshness threshold for the latest captured frame/);
  assert.match(template, /Readiness and health checks report frames older than this as stale/);
  assert.doesNotMatch(template, /Frame Cache Age|re-encod|frame reuse/i);
});
