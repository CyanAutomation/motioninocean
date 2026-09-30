import test from "node:test";
import assert from "node:assert/strict";
import { showWebcamHelpModal } from "../../frontend/src/webcam-help-modal.ts";

function createDependencies(overrides = {}) {
  const calls = [];
  return {
    calls,
    dependencies: {
      fetchReadme: async () => ({ content: "# Help" }),
      openModal: (payload) => calls.push(payload),
      renderMarkdown: (content) => `<article>${content}</article>`,
      sanitizeHtml: (html) => html,
      escapeHtml: (value) => String(value),
      warn: () => {},
      ...overrides,
    },
  };
}

test("showWebcamHelpModal renders sanitized README content", async () => {
  let sanitizedInput = "";
  const { dependencies, calls } = createDependencies({
    fetchReadme: async () => ({ content: "# Help\nDetails" }),
    renderMarkdown: () => '<article><a onclick="evil()">safe</a></article>',
    sanitizeHtml: (html) => {
      sanitizedInput = html;
      return "<article><a>safe</a></article>";
    },
  });

  await showWebcamHelpModal(dependencies);

  assert.equal(calls.length, 2);
  assert.match(calls[0].htmlContent, /Loading help documentation/);
  assert.equal(sanitizedInput, '<article><a onclick="evil()">safe</a></article>');
  assert.equal(calls[1].htmlContent, "<article><a>safe</a></article>");
});

test("showWebcamHelpModal links to documentation when content is unavailable", async () => {
  const { dependencies, calls } = createDependencies({
    fetchReadme: async () => ({
      status: "degraded",
      content: "",
      message: "README unavailable in container image",
      documentation_url: "https://example.com/docs",
    }),
  });

  await showWebcamHelpModal(dependencies);

  assert.match(calls[1].htmlContent, /README unavailable in container image/);
  assert.match(calls[1].htmlContent, /href="https:\/\/example.com\/docs"/);
  assert.match(calls[1].htmlContent, />Open documentation</);
});

test("showWebcamHelpModal escapes content when rendering or sanitizing fails", async () => {
  const warnings = [];
  const { dependencies, calls } = createDependencies({
    fetchReadme: async () => ({ content: "<script>alert(1)</script>" }),
    renderMarkdown: () => {
      throw new Error("renderer failed");
    },
    escapeHtml: (value) => String(value).replace(/</g, "&lt;").replace(/>/g, "&gt;"),
    warn: (...args) => warnings.push(args),
  });

  await showWebcamHelpModal(dependencies);

  assert.equal(warnings.length, 1);
  assert.match(calls[1].htmlContent, /^<pre>/);
  assert.match(calls[1].htmlContent, /&lt;script&gt;alert\(1\)&lt;\/script&gt;/);
});

test("showWebcamHelpModal falls back when sanitization fails", async () => {
  const { dependencies, calls } = createDependencies({
    fetchReadme: async () => ({ content: "# Header" }),
    sanitizeHtml: () => {
      throw new Error("sanitizer failed");
    },
  });

  await showWebcamHelpModal(dependencies);

  assert.equal(calls[1].htmlContent, "<pre># Header</pre>");
});

test("showWebcamHelpModal reports fetch failures", async () => {
  const { dependencies, calls } = createDependencies({
    fetchReadme: async () => {
      throw new Error("network down");
    },
  });

  await showWebcamHelpModal(dependencies);

  assert.equal(calls.length, 2);
  assert.equal(calls[1].htmlContent, "<p>network down</p>");
});
