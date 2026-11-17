import test from "node:test";
import assert from "node:assert/strict";
import { handleStatsUpdateFailure } from "../../frontend/src/stats-update-error.ts";

test("handleStatsUpdateFailure treats timeout errors as retryable without marking stats failed", () => {
  const calls: string[] = [];
  handleStatsUpdateFailure(new DOMException("deadline exceeded", "TimeoutError"), {
    onTimeout: () => calls.push("retry"),
    onFailure: () => calls.push("failure"),
  });

  assert.deepEqual(calls, ["retry"]);
});

test("handleStatsUpdateFailure sends ordinary request errors to the failure handler", () => {
  const error = new Error("offline");
  let received: unknown;
  handleStatsUpdateFailure(error, {
    onTimeout: () => assert.fail("ordinary errors should not schedule a timeout retry"),
    onFailure: (failure) => {
      received = failure;
    },
  });

  assert.equal(received, error);
});
