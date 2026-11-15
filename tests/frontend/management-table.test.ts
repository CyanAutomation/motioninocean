import test from "node:test";
import assert from "node:assert/strict";

import { renderWebcamRows } from "../../frontend/src/management-table.ts";

test("empty webcam tables explain how to add a node", () => {
  const markup = renderWebcamRows({ webcams: [], statuses: new Map() });

  assert.match(markup, /No webcam hosts yet\. Add a webcam to start monitoring it\./);
  assert.doesNotMatch(markup, /webcams-no-match-row/);
});

test("webcam rows escape untrusted values and expose discovery actions", () => {
  const markup = renderWebcamRows({
    webcams: [
      {
        id: 'cam" onmouseover="alert(1)',
        name: "<Camera>",
        base_url: "https://camera.local/?q=\"<script>",
        discovery: { source: "discovered", approved: false },
      },
    ],
    statuses: new Map([
      [
        'cam" onmouseover="alert(1)',
        { status: "ok", ready: true, stream_available: true },
      ],
    ]),
  });

  assert.match(markup, /data-search="[^"]*&quot;[^"]*"/);
  assert.match(markup, /&lt;Camera&gt;/);
  assert.match(markup, /data-status="online"/);
  assert.match(markup, /data-action="approve"/);
  assert.match(markup, /data-action="reject"/);
  assert.match(markup, /data-action="delete"/);
  assert.doesNotMatch(markup, /<script>/);
});

test("failed webcam rows include a filterable attention state and connection reason", () => {
  const markup = renderWebcamRows({
    webcams: [{ id: "cam-1", name: "Hallway", base_url: "http://cam.local" }],
    statuses: new Map([
      ["cam-1", { status: "error", error_code: "NETWORK_UNREACHABLE" }],
    ]),
  });

  assert.match(markup, /data-status="needs-attention"/);
  assert.match(markup, /Node is unreachable on the network/);
  assert.match(markup, /No webcams match these filters/);
});
