import test from "node:test";
import assert from "node:assert/strict";
import { fetchJsonWithTimeout, type JsonFetcher } from "../../frontend/src/fetch-json.ts";

test("fetchJsonWithTimeout passes a timeout signal and returns JSON", async () => {
  const request = { signal: undefined as AbortSignal | undefined };
  const fetcher: JsonFetcher = async (_input, init) => {
    request.signal = init?.signal as AbortSignal;
    return new Response(JSON.stringify({ status: "ok" }), { status: 200 });
  };

  const result = await fetchJsonWithTimeout<{ status: string }>("/metrics", 1000, fetcher);

  assert.deepEqual(result, { status: "ok" });
  assert.ok(request.signal instanceof AbortSignal);
  assert.equal(request.signal.aborted, false);
});

test("fetchJsonWithTimeout preserves the HTTP status error", async () => {
  const fetcher: JsonFetcher = async () => new Response("unavailable", { status: 503 });

  await assert.rejects(
    fetchJsonWithTimeout("/api/config", 1000, fetcher),
    new Error("HTTP error! status: 503"),
  );
});

test("fetchJsonWithTimeout aborts the request with a timeout reason", async () => {
  const request = { signal: undefined as AbortSignal | undefined };
  const fetcher: JsonFetcher = (_input, init) =>
    new Promise((_resolve, reject) => {
      const signal = init?.signal as AbortSignal;
      request.signal = signal;
      signal.addEventListener("abort", () => reject(signal.reason), { once: true });
    });

  const keepEventLoopAlive = setTimeout(() => undefined, 50);
  try {
    await assert.rejects(
      fetchJsonWithTimeout("/metrics", 5, fetcher),
      (error: unknown) => error instanceof DOMException && error.name === "TimeoutError",
    );
  } finally {
    clearTimeout(keepEventLoopAlive);
  }
  assert.equal(request.signal?.aborted, true);
});
