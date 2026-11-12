import test from "node:test";
import assert from "node:assert/strict";
import {
  createStreamReconnectController,
  imageHasLoadedFrame,
  type StreamReconnectDependencies,
} from "../../frontend/src/stream-reconnect.ts";

interface ScheduledTask {
  callback: () => void;
  delayMs: number;
  cancelled: boolean;
}

function createHarness(initiallyVisible = true) {
  const attributes: Record<string, string> = { src: "/stream.mjpg" };
  const image = {
    setAttribute(name: string, value: string) {
      attributes[name] = value;
    },
    removeAttribute(name: string) {
      delete attributes[name];
    },
  };
  const tasks: ScheduledTask[] = [];
  let now = 1000;
  let visible = initiallyVisible;
  const dependencies: StreamReconnectDependencies = {
    currentHref: "https://demo.example/",
    isVisible: () => visible,
    now: () => now,
    schedule: (callback, delayMs) => {
      const task = { callback, delayMs, cancelled: false };
      tasks.push(task);
      return task as unknown as ReturnType<typeof setTimeout>;
    },
    cancel: (timer) => {
      const task = timer as unknown as ScheduledTask;
      task.cancelled = true;
    },
  };
  const controller = createStreamReconnectController(image, "/stream.mjpg", dependencies);

  return {
    attributes,
    controller,
    tasks,
    setNow(value: number) {
      now = value;
    },
    setVisible(value: boolean) {
      visible = value;
    },
    runNextTask() {
      const task = tasks.find((candidate) => !candidate.cancelled);
      assert.ok(task, "expected a pending reconnect task");
      task.cancelled = true;
      task.callback();
    },
  };
}

test("cached stream frames are recognized after the image load event has passed", () => {
  assert.equal(imageHasLoadedFrame({ complete: true, naturalWidth: 640 }), true);
  assert.equal(imageHasLoadedFrame({ complete: true, naturalWidth: 0 }), false);
  assert.equal(imageHasLoadedFrame({ complete: false, naturalWidth: 640 }), false);
});

test("stream errors reconnect with bounded exponential backoff", () => {
  const harness = createHarness();

  harness.controller.onError();
  assert.equal(harness.tasks.at(-1)?.delayMs, 1000);
  harness.runNextTask();
  assert.match(harness.attributes.src, /^https:\/\/demo\.example\/stream\.mjpg\?/);

  harness.controller.onError();
  assert.equal(harness.tasks.at(-1)?.delayMs, 2000);
  harness.controller.onError();
  assert.equal(harness.tasks.at(-1)?.delayMs, 4000);
});

test("a successful stream load resets retry backoff", () => {
  const harness = createHarness();
  harness.controller.onError();
  harness.runNextTask();
  harness.controller.onError();
  assert.equal(harness.tasks.at(-1)?.delayMs, 2000);

  harness.controller.onLoad();
  harness.controller.onError();

  assert.equal(harness.tasks.at(-1)?.delayMs, 1000);
});

test("hidden pages close the stream and visible pages reconnect", () => {
  const harness = createHarness();
  harness.controller.onError();
  const pendingTask = harness.tasks.at(-1);
  harness.setVisible(false);
  harness.controller.onVisibilityChange();

  assert.equal(pendingTask?.cancelled, true);
  assert.equal(harness.attributes.src, undefined);

  harness.controller.onError();
  assert.equal(harness.tasks.filter((task) => !task.cancelled).length, 0);

  harness.setVisible(true);
  harness.setNow(2500);
  harness.controller.onVisibilityChange();
  assert.match(harness.attributes.src, /_stream_retry=2500/);
});

test("manual refresh cancels retries and dispose stops future reconnects", () => {
  const harness = createHarness();
  harness.controller.onError();
  const pendingTask = harness.tasks.at(-1);
  harness.controller.refresh();
  assert.equal(pendingTask?.cancelled, true);

  harness.controller.dispose();
  harness.controller.onError();
  assert.equal(harness.tasks.filter((task) => !task.cancelled).length, 0);
  assert.equal(harness.attributes.src, undefined);
});
