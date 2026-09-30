import test from "node:test";
import assert from "node:assert/strict";
import { applyMockStreamMode } from "../../frontend/src/mock-stream-ui.ts";
import { setActiveView } from "../../frontend/src/management-navigation.ts";
import {
  renderDiscoveredPanel,
  renderOverviewPanel,
} from "../../frontend/src/management-renderers.ts";
import { recordStatusHistory } from "../../frontend/src/management-status.ts";
import { collectSetupConfig } from "../../frontend/src/setup-config.ts";
import {
  fetchReadmeContent,
  renderMarkdownContent,
} from "../../frontend/src/webcam-help.ts";

function createClassList() {
  const values = new Set();
  return {
    toggle(name, force) {
      const enabled = force ?? !values.has(name);
      enabled ? values.add(name) : values.delete(name);
    },
    contains(name) {
      return values.has(name);
    },
  };
}

class MockHTMLElement {
  constructor() {
    this.classList = createClassList();
    this.attributes = new Map();
    this.innerHTML = "";
    this.textContent = "";
  }

  setAttribute(name, value) {
    this.attributes.set(name, value);
  }
}

class MockHTMLButtonElement extends MockHTMLElement {}

test("collectSetupConfig reads defaults and parses wizard inputs", () => {
  const values = new Map([
    ["setup-resolution", "1280x720"],
    ["setup-fps", "24fps"],
    ["setup-jpeg-quality", "0"],
    ["setup-max-connections", "invalid"],
    ["setup-target-fps", "30fps"],
    ["setup-pi3-profile", "true"],
    ["setup-cors-origins", "https://example.test"],
    ["setup-mock-camera", "false"],
    ["setup-auth-token", "secret"],
  ]);
  const documentRef = {
    getElementById: (id) => (values.has(id) ? { value: values.get(id) } : null),
  };
  assert.deepEqual(collectSetupConfig(documentRef), {
    resolution: "1280x720",
    fps: 24,
    jpeg_quality: 90,
    max_connections: 10,
    target_fps: 30,
    pi3_profile: true,
    cors_origins: "https://example.test",
    mock_camera: false,
    auth_token: "secret",
  });

  documentRef.getElementById = () => null;
  assert.deepEqual(collectSetupConfig(documentRef), {
    resolution: "",
    fps: 0,
    jpeg_quality: 90,
    max_connections: 10,
    target_fps: null,
    pi3_profile: false,
    cors_origins: "",
    mock_camera: false,
    auth_token: "",
  });
});

test("fetchReadmeContent normalizes successful and degraded API responses", async () => {
  const responses = [
    { ok: true, json: async () => ({ content: "# Help", source: "readme" }) },
    {
      ok: false,
      json: async () => ({ status: "degraded", message: "README unavailable" }),
    },
  ];
  let request;
  const fetcher = async (...args) => {
    request = args;
    return responses.shift();
  };

  assert.deepEqual(await fetchReadmeContent(fetcher), {
    status: "ok",
    content: "# Help",
    message: "",
    documentation_url: "",
    source: "readme",
  });
  assert.deepEqual(request, [
    "/api/help/readme",
    { headers: { Accept: "application/json, text/plain" } },
  ]);
  assert.deepEqual(await fetchReadmeContent(fetcher), {
    status: "degraded",
    content: "",
    message: "README unavailable",
    documentation_url: "",
    source: "",
  });
});

test("fetchReadmeContent throws a useful error for non-degraded failures", async () => {
  const fetcher = async () => ({ ok: false, json: async () => ({ message: "request denied" }) });
  await assert.rejects(fetchReadmeContent(fetcher), /request denied/);
});

test("renderMarkdownContent keeps supported blocks escaped and correctly grouped", () => {
  assert.equal(
    renderMarkdownContent(
      "# Guide\n\nFirst **bold** paragraph.\ncontinued.\n\n- one\n- two\n1. three\n\n```html\n<script>\n```",
    ),
    '<article class="utility-modal__markdown"><h1>Guide</h1><p>First <strong>bold</strong> paragraph. continued.</p><ul><li>one</li><li>two</li></ul><ol><li>three</li></ol><pre><code>&lt;script&gt;\n</code></pre></article>',
  );
});

test("setActiveView updates selected panels, navigation controls, and the hash", () => {
  const element = () => new MockHTMLElement();
  const button = () => new MockHTMLButtonElement();
  const views = Object.fromEntries(
    ["overview", "devices", "discovered", "settings"].map((key) => [key, element()]),
  );
  const buttons = Object.fromEntries(
    ["overview", "devices", "discovered", "settings"].map((key) => [key, button()]),
  );
  const railButtons = Object.fromEntries(
    ["overview", "devices", "discovered", "settings"].map((key) => [key, [button(), button()]]),
  );
  const location = { hash: "#overview" };
  let historyUpdates = 0;
  const context = {
    views,
    buttons,
    railButtons,
    location,
    history: {
      replaceState: (_state, _title, hash) => {
        historyUpdates += 1;
        location.hash = hash;
      },
    },
  };

  setActiveView("discovered", Object.keys(views), context);
  assert.equal(views.discovered.classList.contains("hidden"), false);
  assert.equal(views.overview.classList.contains("hidden"), true);
  assert.equal(buttons.discovered.classList.contains("management-view-btn--active"), true);
  assert.equal(buttons.discovered.attributes.get("aria-current"), "page");
  assert.equal(railButtons.discovered[0].classList.contains("rail-btn--active"), true);
  assert.equal(railButtons.discovered[1].classList.contains("mobile-rail-btn--active"), true);
  assert.equal(location.hash, "#discovered");
  assert.equal(historyUpdates, 1);

  setActiveView("invalid", Object.keys(views), context);
  assert.equal(historyUpdates, 1);
});

test("renderOverviewPanel displays summary, activity, and actionable node states", () => {
  const total = new MockHTMLElement();
  const activity = new MockHTMLElement();
  const actions = new MockHTMLElement();
  const context = {
    snapshot: {
      total_webcams: 3,
      healthy_webcams: 1,
      unavailable_webcams: 2,
      stream_available_webcams: 1,
    },
    totalElement: total,
    healthyElement: new MockHTMLElement(),
    unavailableElement: new MockHTMLElement(),
    streamingElement: new MockHTMLElement(),
    activityElement: activity,
    actionElement: actions,
    activityFeed: [{ timestamp: "2026-01-01T12:00:00Z", message: "Node recovered." }],
    statuses: new Map([
      ["a", { error_code: "WEBCAM_UNAUTHORIZED" }],
      ["b", { error_code: "SSRF_BLOCKED" }],
    ]),
    pendingDiscoveryCount: 1,
    escapeHtml: (value) => String(value).replace(/</g, "&lt;").replace(/>/g, "&gt;"),
  };
  renderOverviewPanel(context);

  assert.equal(total.textContent, "3");
  assert.match(activity.innerHTML, /Node recovered\./);
  assert.match(actions.innerHTML, /Auth remediation needed on 1 node/);
  assert.match(actions.innerHTML, /1 discovered device/);
  assert.match(actions.innerHTML, /1 node\(s\) blocked by safety rules/);
});

test("renderDiscoveredPanel selects a visible node and disables decisions when empty", () => {
  const discoveredList = new MockHTMLElement();
  const discoveredNotes = new MockHTMLElement();
  const buttons = [
    new MockHTMLButtonElement(),
    new MockHTMLButtonElement(),
    new MockHTMLButtonElement(),
  ];
  const nodes = [
    { id: "node-1", name: "<camera>", base_url: "http://camera.local" },
    { id: "node-2", name: "Other", base_url: "http://other.local" },
  ];
  const context = {
    nodes,
    selectedNodeId: "missing",
    listElement: discoveredList,
    notesElement: discoveredNotes,
    statuses: new Map([
      ["node-1", { error_message: "<blocked>", error_details: "Private address" }],
    ]),
    snoozedIds: new Set(["node-2"]),
    actionButtons: buttons,
    escapeHtml: (value) => String(value).replace(/</g, "&lt;").replace(/>/g, "&gt;"),
  };

  let selectedNodeId = renderDiscoveredPanel(context);
  assert.equal(selectedNodeId, "node-1");
  assert.match(discoveredList.innerHTML, /&lt;camera&gt;/);
  assert.match(discoveredNotes.innerHTML, /&lt;blocked&gt;/);
  assert.equal(
    buttons.every((candidate) => candidate.disabled === false),
    true,
  );

  context.nodes = [];
  selectedNodeId = renderDiscoveredPanel({ ...context, selectedNodeId });
  assert.equal(selectedNodeId, "");
  assert.match(discoveredList.innerHTML, /No discovered devices pending approval/);
  assert.equal(
    buttons.every((candidate) => candidate.disabled === true),
    true,
  );
});

test("recordStatusHistory announces initialization, transitions, and recovery", () => {
  const events = [];
  const history = new Map();

  recordStatusHistory(
    new Map([["node-a", { status: "error", error_code: "DOWN" }]]),
    history,
    (...args) => events.push(args),
  );
  recordStatusHistory(new Map([["node-a", { status: "ok" }]]), history, (...args) =>
    events.push(args),
  );

  assert.deepEqual(JSON.parse(JSON.stringify(events)), [
    ["node-a status initialized: error."],
    ["node-a status changed to ok."],
    ["node-a recovered.", "success"],
  ]);
  assert.equal(history.get("node-a").status, "ok");
});

test("applyMockStreamMode updates stream appearance, controls, animation, and mock status", () => {
  const toggles = [];
  const placeholder = { hidden: true };
  const animation = {
    classList: { toggle: (...args) => toggles.push(args) },
    attributes: { data: "/mock.svg" },
    getAttribute(name) {
      return this.attributes[name] ?? null;
    },
    removeAttribute(name) {
      delete this.attributes[name];
    },
    setAttribute(name, value) {
      this.attributes[name] = value;
    },
  };
  const video = {
    style: {},
    attributes: {},
    setAttribute(name, value) {
      this.attributes[name] = value;
    },
  };
  const refresh = { title: "" };
  const fullscreen = { title: "" };
  const compactRefresh = { title: "" };
  const compactFullscreen = { title: "" };
  const statuses = [];

  applyMockStreamMode(true, true, {
    elements: {
      videoStream: video,
      mockStreamPlaceholder: placeholder,
      mockStreamAnimation: animation,
      refreshBtn: refresh,
      fullscreenBtn: fullscreen,
    },
    document: {
      getElementById: (id) =>
        id === "vc-refresh-btn"
          ? compactRefresh
          : id === "vc-fullscreen-btn"
            ? compactFullscreen
            : null,
    },
    setConnectionStatus: (...args) => statuses.push(args),
  });

  assert.equal(placeholder.hidden, false);
  assert.deepEqual(video.style, { opacity: "0.2", filter: "grayscale(1)" });
  assert.equal(video.attributes["aria-hidden"], "true");
  assert.equal(animation.attributes.data, "/mock.svg");
  assert.deepEqual(toggles, [["mock-stream-animation--failed", false]]);
  assert.equal(refresh.title, "Refresh stream (mock mode active)");
  assert.equal(fullscreen.title, "Toggle fullscreen (mock preview)");
  assert.equal(compactRefresh.title, refresh.title);
  assert.equal(compactFullscreen.title, fullscreen.title);
  assert.deepEqual(statuses, [["inactive", "Mock fallback active (camera unavailable)"]]);
});
