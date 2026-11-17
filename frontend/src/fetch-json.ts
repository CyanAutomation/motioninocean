/**
 * Fetch and parse a JSON response with a declarative timeout signal.
 *
 * @template T - Expected response payload type.
 * @param input - Request URL or request object.
 * @param timeoutMs - Deadline in milliseconds.
 * @param fetcher - Fetch implementation; defaults to the global fetch function.
 * @returns Parsed JSON response typed as T.
 * @throws {Error} If the request fails, times out, or returns a non-OK status.
 * @async
 */
export async function fetchJsonWithTimeout<T>(
  input: Parameters<typeof fetch>[0],
  timeoutMs: number,
  fetcher: JsonFetcher = fetch,
): Promise<T> {
  const response = await fetcher(input, { signal: AbortSignal.timeout(timeoutMs) });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return (await response.json()) as T;
}

/**
 * Check whether a request failure represents a deadline or an abort.
 *
 * AbortError remains supported for callers that use AbortController directly, while
 * AbortSignal.timeout() rejects with TimeoutError.
 *
 * @param error - Caught request failure.
 * @returns Whether the failure came from an abort or request deadline.
 */
export function isRequestTimeoutError(error: unknown): boolean {
  return (
    typeof error === "object" &&
    error !== null &&
    "name" in error &&
    (error.name === "TimeoutError" || error.name === "AbortError")
  );
}

/** Fetch implementation accepted by fetchJsonWithTimeout. */
export type JsonFetcher = typeof fetch;
