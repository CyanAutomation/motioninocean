import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { applyMockStreamMode, type MockStreamContext } from "../../frontend/src/mock-stream-ui.ts";
import { asTestDouble } from "./test-doubles.ts";

function extractFunction(source: string, functionName: string): string {
  const match = source.match(
    new RegExp(`function ${functionName}\\([^)]*\\) \\{[\\s\\S]*?\\n^}`, "m"),
  );
  if (!match) {
    throw new Error(`${functionName}() definition not found`);
  }
  return match[0];
}

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

test("mock stream visibility updates do not alter hero mascot behavior", () => {
  const appJs = fs.readFileSync("pi_camera_in_docker/static/js/app.js", "utf8");
  const getMioAssetsFn = extractFunction(appJs, "getMioAssets");
  const updateMascotForTabFn = extractFunction(appJs, "updateMascotForTab");

  const heroImage = { src: "", alt: "" };
  const context = {
    DEFAULT_MIO_PATH: "/static/img/mio/default.png",
    document: {
      body: {
        dataset: {
          mioAvatar: "/static/img/mio/mio_avatar.png",
          mioHappy: "/static/img/mio/mio_happy.png",
          mioCurious: "/static/img/mio/mio_curious.png",
          mioSleeping: "/static/img/mio/mio_sleeping.png",
          mioWinking: "/static/img/mio/mio_winking.png",
          mioFloating: "/static/img/mio/mio_floating.svg",
        },
      },
      getElementById: (_id: string) => null,
    },
    state: {
      elements: {
        mioHeroImage: heroImage,
        videoStream: {
          style: {},
          setAttribute() {},
        },
        mockStreamPlaceholder: { hidden: true },
      },
    },
    setConnectionStatus: () => {},
  };

  vm.runInNewContext(`${getMioAssetsFn}\n${updateMascotForTabFn};`, context);

  const evaluatedContext = asTestDouble<typeof context & { updateMascotForTab(tab: string): void }>(
    context,
  );
  evaluatedContext.updateMascotForTab("settings");
  const before = { ...heroImage };

  const streamContext = asTestDouble<MockStreamContext>({
    elements: {
      videoStream: context.state.elements.videoStream,
      mockStreamPlaceholder: context.state.elements.mockStreamPlaceholder,
      mockStreamAnimation: null,
      refreshBtn: null,
      fullscreenBtn: null,
    },
    document: context.document,
    setConnectionStatus: context.setConnectionStatus,
  });
  applyMockStreamMode(true, true, streamContext);
  applyMockStreamMode(false, false, streamContext);

  assert.deepEqual(heroImage, before);
});
