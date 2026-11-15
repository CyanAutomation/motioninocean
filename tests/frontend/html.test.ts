import test from "node:test";
import assert from "node:assert/strict";

import { escapeHtml } from "../../frontend/src/html.ts";

test("HTML escaping protects text and quoted attribute values", () => {
  assert.equal(escapeHtml(`<tag attr="value">&'`), "&lt;tag attr=&quot;value&quot;&gt;&amp;&#39;");
  assert.equal(escapeHtml(null), "");
  assert.equal(escapeHtml(42), "42");
});
