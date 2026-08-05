import test from "node:test";
import assert from "node:assert/strict";

import { renderConfig } from "../../pi_camera_in_docker/static/js/config-renderer.js";
import { renderMetrics } from "../../pi_camera_in_docker/static/js/metrics-renderer.js";

function element() {
  return { textContent: "", dataset: {}, classList: { toggle() {} } };
}

test("renderMetrics renders connected stream metrics through the supplied dependencies", () => {
  const state = {
    elements: Object.fromEntries(
      [
        "fpsValue",
        "chipFps",
        "performanceRiskValue",
        "uptimeValue",
        "framesRiskDetail",
        "lastFrameAgeValue",
        "lastFrameRiskValue",
        "maxFrameAgeValue",
        "maxFrameRiskValue",
        "streamRiskValue",
        "resolutionValue",
        "lastUpdated",
      ].map((key) => [key, element()]),
    ),
  };
  const statuses = [];
  let resetCalls = 0;
  let increaseCalls = 0;

  renderMetrics(
    {
      camera_active: true,
      current_fps: 12.34,
      uptime_seconds: 65,
      frames_captured: 1234,
      last_frame_age_seconds: 0.2,
      max_frame_age_seconds: 1,
      resolution: [640, 480],
    },
    {
      state,
      setConnectionStatus: (...args) => statuses.push(args),
      resetBackoff: () => resetCalls++,
      increaseBackoff: () => increaseCalls++,
      formatUptime: (value) => `${value}s`,
      formatNumber: (value) => String(value),
      formatSeconds: (value) => `${value}s`,
      updateConnectionDisplays: () => {},
    },
  );

  assert.deepEqual(statuses, [["connected", "Connected"]]);
  assert.equal(resetCalls, 1);
  assert.equal(increaseCalls, 0);
  assert.equal(state.elements.fpsValue.textContent, "12.3");
  assert.equal(state.elements.resolutionValue.textContent, "640 × 480");
});

test("renderConfig renders partial configuration and derives overall health", () => {
  const values = new Map();
  const indicators = new Map();
  const state = { streamConnections: { current: "--", max: "--" } };

  renderConfig(
    {
      camera_settings: { resolution: [1280, 720], fps: 24 },
      stream_control: { max_stream_connections: 5, current_stream_connections: 2 },
      runtime: { camera_active: true, mock_camera: false, uptime_seconds: 10 },
      health_check: {
        camera_pipeline: { state: "ok" },
        stream_freshness: { state: "warn" },
      },
    },
    {
      state,
      setConfigValue: (id, value) => values.set(id, value),
      formatBoolean: (value) => String(value),
      formatUptime: (value) => `${value}s`,
      applyMockStreamMode: () => {},
      setHealthIndicator: (id, value) => indicators.set(id, value),
      normalizeHealthState: (value) => value,
      healthText: { ok: "OK", warn: "Warning", fail: "Failed", unknown: "Unknown" },
      updateConnectionDisplays: () => {},
    },
  );

  assert.equal(values.get("config-resolution"), "1280 × 720");
  assert.equal(values.get("config-fps"), "24 FPS");
  assert.equal(state.streamConnections.current, 2);
  assert.equal(state.streamConnections.max, 5);
  assert.equal(indicators.get("config-health-overall").state, "warn");
});
