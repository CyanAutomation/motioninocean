import test from "node:test";
import assert from "node:assert/strict";

import { renderChangelogHtml } from "../../frontend/src/webcam-changelog.ts";

test("changelog rendering escapes entry content and shows only the first three releases", () => {
  const markup = renderChangelogHtml(
    {
      status: "ok",
      entries: [
        {
          version: "1.4",
          release_date: "<today>",
          changes: ['<img src="x"> & safer output'],
        },
        { version: "1.3", release_date: null, changes: [] },
        { version: "1.2", release_date: "2026-01-01", changes: ["Third release"] },
        { version: "1.1", release_date: "2025-12-01", changes: ["Hidden release"] },
      ],
      full_changelog_url: " https://example.test/changelog?a=1&b=2 ",
    },
    false,
  );

  assert.match(markup, /v1\.4/);
  assert.match(markup, /&lt;img src=&quot;x&quot;&gt; &amp; safer output/);
  assert.match(markup, /Unknown date/);
  assert.match(markup, /https:\/\/example\.test\/changelog\?a=1&amp;b=2/);
  assert.doesNotMatch(markup, /Hidden release|v1\.1/);
  assert.doesNotMatch(markup, /<img src=/);
});

test("changelog rendering provides empty-state copy and safe degraded diagnostics", () => {
  const empty = renderChangelogHtml({ status: "ok", entries: [] }, false);
  assert.match(empty, /No changelog entries available/);

  const degraded = {
    status: "degraded",
    entries: [],
    message: "<private detail>",
    source: "cache & fallback",
  };
  const normalMarkup = renderChangelogHtml(degraded, false);
  assert.match(normalMarkup, /couldn&#39;t load the latest changelog details/);
  assert.doesNotMatch(normalMarkup, /private detail|cache &amp; fallback/);

  const debugMarkup = renderChangelogHtml(degraded, true);
  assert.match(debugMarkup, /&lt;private detail&gt;/);
  assert.match(debugMarkup, /cache &amp; fallback/);
});

test("changelog rendering omits links with unsafe or relative URL schemes", () => {
  for (const url of [
    "javascript:alert(document.cookie)",
    "data:text/html,<script>alert(1)</script>",
    "//example.test/changelog",
  ]) {
    const markup = renderChangelogHtml(
      { status: "ok", entries: [], full_changelog_url: url },
      false,
    );

    assert.doesNotMatch(markup, /View full changelog/);
    assert.doesNotMatch(markup, /href=/);
  }
});
