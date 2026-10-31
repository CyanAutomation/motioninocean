import test from "node:test";
import assert from "node:assert/strict";
import { bindOptionalEventListeners } from "../../frontend/src/app-event-bindings.ts";

test("bindOptionalEventListeners attaches all listeners to available targets", () => {
  const firstTarget = new EventTarget();
  const secondTarget = new EventTarget();
  let firstCalls = 0;
  let secondCalls = 0;
  bindOptionalEventListeners([
    { target: firstTarget, type: "first", listener: () => firstCalls++ },
    { target: secondTarget, type: "second", listener: () => secondCalls++ },
    {
      target: null,
      type: "missing",
      listener: () => assert.fail("missing target was invoked"),
    },
    {
      target: undefined,
      type: "missing-too",
      listener: () => assert.fail("missing target was invoked"),
    },
  ]);

  firstTarget.dispatchEvent(new Event("first"));
  firstTarget.dispatchEvent(new Event("second"));
  secondTarget.dispatchEvent(new Event("second"));
  assert.equal(firstCalls, 1);
  assert.equal(secondCalls, 1);
});
