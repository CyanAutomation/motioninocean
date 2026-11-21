import test from "node:test";
import assert from "node:assert/strict";

import { validateSoyuzBaseUrl } from "../../scripts/validate-soyuz-url.ts";
import { validateSoyuzRunId } from "../../scripts/validate-soyuz-run-id.ts";

const soyuzOrigin = "https://soyuz.scheimann.workers.dev";

test("Soyuz URL validation accepts the approved origin and normalizes a trailing slash", () => {
  assert.equal(validateSoyuzBaseUrl(soyuzOrigin), soyuzOrigin);
  assert.equal(validateSoyuzBaseUrl(`${soyuzOrigin}/`), soyuzOrigin);
});

test("Soyuz URL validation rejects missing, malformed, or unsafe URLs", () => {
  for (const value of [
    undefined,
    "",
    "   ",
    "not a URL",
    "http://soyuz.scheimann.workers.dev",
    "https://soyuz.example.com",
    `${soyuzOrigin}/api`,
    `${soyuzOrigin}?token=secret`,
    `${soyuzOrigin}#fragment`,
    "https://user:password@soyuz.scheimann.workers.dev",
    `${soyuzOrigin} /path`,
  ]) {
    assert.throws(() => validateSoyuzBaseUrl(value));
  }
});

test("Soyuz run ID validation accepts UUIDv7 IDs only", () => {
  const validRunId = "018f47d0-1234-7abc-8def-0123456789ab";
  assert.equal(validateSoyuzRunId(validRunId), validRunId);

  for (const value of [
    undefined,
    "",
    "018f47d0-1234-4abc-8def-0123456789ab",
    "not-a-uuid",
    "018f47d0-1234-7abc-cdef-0123456789ab",
  ]) {
    assert.throws(() => validateSoyuzRunId(value));
  }
});
