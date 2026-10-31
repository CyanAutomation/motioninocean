import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { createSnackbarController } from "../../frontend/src/snackbar.ts";

function createRegion() {
  const classes = new Set<string>();
  const listeners = new Map<string, Array<(event: { relatedTarget?: unknown }) => void>>();
  const dismissListeners: Array<() => void> = [];
  const message = { textContent: "" };
  const dismiss = { addEventListener: (_name: string, handler: () => void) => dismissListeners.push(handler) };
  function listen(name: string, handler: (event: { relatedTarget?: unknown }) => void) {
    const items = listeners.get(name) ?? [];
    items.push(handler);
    listeners.set(name, items);
  }
  const region = {
    classList: {
      add: (name: string) => classes.add(name),
      remove: (name: string) => classes.delete(name),
      contains: (name: string) => classes.has(name),
    },
    addEventListener: listen,
    contains: (element: unknown) => element === dismiss,
    querySelector: (selector: string) => selector === "[data-snackbar-message]" ? message : dismiss,
  };
  return {
    region,
    message,
    dismiss,
    classes,
    fire(name: string, event: { relatedTarget?: unknown } = {}) {
      for (const handler of listeners.get(name) ?? []) handler(event);
    },
    fireDismiss() { for (const handler of dismissListeners) handler(); },
  };
}

function createClock() {
  let callback: (() => void) | null = null;
  let delay = 0;
  return {
    setTimeout(handler: () => void, ms: number) {
      callback = handler;
      delay = ms;
      return 1;
    },
    clearTimeout() { callback = null; },
    fire() { callback?.(); callback = null; },
    get delay() { return delay; },
  };
}

test("snackbar shows a polite confirmation and dismisses it after five seconds", () => {
  const { region, message, classes } = createRegion();
  const clock = createClock();
  const snackbar = createSnackbarController(region as never, clock);

  snackbar.show("Settings saved.");
  assert.equal(message.textContent, "Settings saved.");
  assert.equal(classes.has("snackbar--visible"), true);
  assert.equal(clock.delay, 5000);

  clock.fire();
  assert.equal(classes.has("snackbar--visible"), false);
});

test("snackbar replaces an active message and pauses while hovered or focused", () => {
  const { region, message, classes, fire, dismiss } = createRegion();
  const clock = createClock();
  const snackbar = createSnackbarController(region as never, clock);

  snackbar.show("First");
  snackbar.show("Second");
  assert.equal(message.textContent, "Second");
  assert.equal(clock.delay, 5000);

  fire("pointerenter");
  clock.fire();
  assert.equal(classes.has("snackbar--visible"), true);
  fire("pointerleave");
  assert.equal(clock.delay, 5000);

  fire("focusin");
  fire("focusout", { relatedTarget: dismiss });
  assert.equal(classes.has("snackbar--visible"), true);
  fire("focusout", { relatedTarget: null });
  clock.fire();
  assert.equal(classes.has("snackbar--visible"), false);
});

test("leaving with the pointer does not resume while keyboard focus remains", () => {
  const { region, classes, fire } = createRegion();
  const clock = createClock();
  const snackbar = createSnackbarController(region as never, clock);

  snackbar.show("Saved.");
  fire("pointerenter");
  fire("focusin");
  fire("pointerleave");
  clock.fire();

  assert.equal(classes.has("snackbar--visible"), true);
});

test("moving focus away does not resume while the pointer remains over the snackbar", () => {
  const { region, classes, fire } = createRegion();
  const clock = createClock();
  const snackbar = createSnackbarController(region as never, clock);

  snackbar.show("Saved.");
  fire("pointerenter");
  fire("focusin");
  fire("focusout", { relatedTarget: null });
  clock.fire();

  assert.equal(classes.has("snackbar--visible"), true);
});

test("snackbar dismiss button closes it immediately", () => {
  const { region, classes, fireDismiss } = createRegion();
  const clock = createClock();
  const snackbar = createSnackbarController(region as never, clock);
  snackbar.show("Copied.");
  fireDismiss();
  assert.equal(classes.has("snackbar--visible"), false);
});

test("both app shells provide an accessible snackbar region", () => {
  for (const path of [
    "pi_camera_in_docker/templates/index.html",
    "pi_camera_in_docker/templates/management.html",
  ]) {
    const template = fs.readFileSync(path, "utf8");
    assert.match(template, /id="app-snackbar"[^>]*role="status"[^>]*aria-live="polite"/);
    assert.match(template, /data-snackbar-message/);
    assert.match(template, /data-snackbar-dismiss/);
  }
});
