import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { applyMockStreamMode, type MockStreamContext } from "../../frontend/src/mock-stream-ui.ts";
import { asTestDouble } from "./test-doubles.ts";

test("applyMockStreamMode toggles placeholder visibility for mock runtime states", () => {
  const placeholder = { hidden: true };
  const video = {
    style: { opacity: "", filter: "" },
    attributes: {} as Record<string, string>,
    setAttribute(name: string, value: string) {
      this.attributes[name] = value;
    },
  };

  const context = {
    state: {
      elements: {
        videoStream: video,
        mockStreamPlaceholder: placeholder,
        mockStreamAnimation: {
          attributes: { data: "/static/img/mio/mio_mock_stream.svg" } as Record<string, string>,
          classList: { toggle: (_name: string, _force?: boolean) => {} },
          getAttribute(name: string) {
            return this.attributes[name] ?? null;
          },
          removeAttribute(name: string) {
            delete this.attributes[name];
          },
          setAttribute(name: string, value: string) {
            this.attributes[name] = value;
          },
        },
        refreshBtn: { title: "" },
        fullscreenBtn: { title: "" },
      },
    },
    document: {
      getElementById: () => null,
    },
    setConnectionStatus: () => {},
  };

  const streamContext = asTestDouble<MockStreamContext>({
    elements: context.state.elements,
    document: context.document,
    setConnectionStatus: context.setConnectionStatus,
  });
  applyMockStreamMode(true, false, streamContext);
  assert.equal(placeholder.hidden, false);
  assert.equal(video.style.opacity, "0.2");
  assert.equal(video.attributes["aria-hidden"], "true");

  applyMockStreamMode(false, false, streamContext);
  assert.equal(placeholder.hidden, true);
  assert.equal(video.style.opacity, "1");
  assert.equal(video.attributes["aria-hidden"], "false");
});

test("mock placeholder template preserves animation host contract", () => {
  const template = fs.readFileSync("pi_camera_in_docker/templates/index.html", "utf8");

  const placeholderMatch = template.match(/<div\s+id="mock-stream-placeholder"[\s\S]*?<\/div>/);

  assert.ok(placeholderMatch, "mock placeholder container should exist");
  const placeholderMarkup = placeholderMatch[0];

  assert.match(
    placeholderMarkup,
    /<object\s+id="mock-stream-animation"[\s\S]*?type="image\/svg\+xml"/,
    "mock placeholder should include an embedded object animation host",
  );
  assert.match(
    placeholderMarkup,
    /class="mock-stream-placeholder"/,
    "mock placeholder should keep stable class contract",
  );
  assert.doesNotMatch(
    placeholderMarkup,
    /<img\b/,
    "mock placeholder should avoid legacy unbounded image-only embedding",
  );
});
