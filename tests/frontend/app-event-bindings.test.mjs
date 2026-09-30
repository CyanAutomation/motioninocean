import test from "node:test";
import assert from "node:assert/strict";
import { bindOptionalEventListeners } from "../../frontend/src/app-event-bindings.ts";

test("bindOptionalEventListeners attaches all listeners to available targets", () => {
  const target = new EventTarget();
  let calls = 0;
  bindOptionalEventListeners([
    { target, type: "first", listener: () => calls++ },
    { target, type: "second", listener: () => calls++ },
    { target: null, type: "missing", listener: () => calls++ },
  ]);

  target.dispatchEvent(new Event("first"));
  target.dispatchEvent(new Event("second"));
  assert.equal(calls, 2);
});

test("bindOptionalEventListeners tolerates an empty binding list", () => {
  assert.doesNotThrow(() => bindOptionalEventListeners([]));
});
