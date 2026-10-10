import test from "node:test";
import assert from "node:assert/strict";
import {
  toggleFullscreen,
  type FullscreenContainer,
  type FullscreenDocument,
} from "../../frontend/src/fullscreen.ts";

function captureLogger() {
  const warnings: string[] = [];
  const errors: string[] = [];
  return {
    logger: {
      warn: (message: string) => {
        warnings.push(message);
      },
      error: (message: string) => {
        errors.push(message);
      },
    },
    warnings,
    errors,
  };
}

test("toggleFullscreen enters and exits native fullscreen", async () => {
  const calls: string[] = [];
  const container: FullscreenContainer = {
    requestFullscreen: () => {
      calls.push("enter");
    },
  };
  const fullscreenDocument: FullscreenDocument = {
    fullscreenElement: null,
    exitFullscreen: () => {
      calls.push("exit");
    },
  };

  await toggleFullscreen(container, fullscreenDocument);
  assert.deepEqual(calls, ["enter"]);

  fullscreenDocument.fullscreenElement = container;
  await toggleFullscreen(container, fullscreenDocument);
  assert.deepEqual(calls, ["enter", "exit"]);
});

test("toggleFullscreen falls back through browser-prefixed enter and exit methods", async () => {
  const calls: string[] = [];
  const container = {
    webkitRequestFullscreen: () => {
      calls.push("webkit-enter");
    },
  };
  const fullscreenDocument = {
    mozFullScreenElement: {},
    msExitFullscreen: () => {
      calls.push("ms-exit");
    },
  };

  await toggleFullscreen(container, fullscreenDocument);
  assert.deepEqual(calls, ["ms-exit"]);

  await toggleFullscreen(container, {});
  assert.deepEqual(calls, ["ms-exit", "webkit-enter"]);
});

test("toggleFullscreen supports Mozilla prefixed APIs", async () => {
  const calls: string[] = [];
  await toggleFullscreen(
    {
      mozRequestFullScreen: () => {
        calls.push("moz-enter");
      },
    },
    {},
  );
  await toggleFullscreen(
    {},
    {
      mozFullScreenElement: {},
      mozCancelFullScreen: () => {
        calls.push("moz-exit");
      },
    },
  );
  assert.deepEqual(calls, ["moz-enter", "moz-exit"]);
});

test("toggleFullscreen supports remaining WebKit and Microsoft prefixed APIs", async () => {
  const calls: string[] = [];
  await toggleFullscreen(
    {
      msRequestFullscreen: () => {
        calls.push("ms-enter");
      },
    },
    {},
  );
  await toggleFullscreen(
    {},
    {
      webkitFullscreenElement: {},
      webkitExitFullscreen: () => {
        calls.push("webkit-exit");
      },
    },
  );
  assert.deepEqual(calls, ["ms-enter", "webkit-exit"]);
});

test("toggleFullscreen handles a missing container and unsupported APIs", async () => {
  const { logger, warnings, errors } = captureLogger();
  await toggleFullscreen(null, {}, logger);
  await toggleFullscreen({}, {}, logger);
  assert.deepEqual(warnings, ["Fullscreen API is not supported in this browser"]);
  assert.deepEqual(errors, []);
});

test("toggleFullscreen reports browser API failures", async () => {
  const { logger, errors } = captureLogger();
  const failure = new Error("denied");
  await toggleFullscreen({ requestFullscreen: () => Promise.reject(failure) }, {}, logger);
  assert.equal(errors.length, 1);
  assert.equal(errors[0], "Failed to toggle fullscreen:");
});
