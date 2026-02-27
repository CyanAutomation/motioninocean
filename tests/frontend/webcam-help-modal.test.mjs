import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

function extractFunction(source, functionName) {
  const match = source.match(
    new RegExp(`async function ${functionName}\\([^)]*\\) \\{[\\s\\S]*?\\n^}`, "m"),
  );
  if (!match) {
    throw new Error(`${functionName}() definition not found`);
  }
  return match[0];
}

function extractSyncFunction(source, functionName) {
  const match = source.match(new RegExp(`function ${functionName}\\([^)]*\\) \\{[\\s\\S]*?\\n^}`, "m"));
  if (!match) {
    throw new Error(`${functionName}() definition not found`);
  }
  return match[0];
}

test("openHelpModal shows fallback messaging when README fetch fails", async () => {
  const appJs = fs.readFileSync("pi_camera_in_docker/static/js/app.js", "utf8");
  const openHelpModalFn = extractFunction(appJs, "openHelpModal");

  const modalCalls = [];
  const context = {
    fetchReadmeContent: async () => {
      throw new Error("network down");
    },
    openUtilityModal: (payload) => {
      modalCalls.push(payload);
    },
    escapeHtml: (value) => String(value),
    Error,
  };

  vm.runInNewContext(`${openHelpModalFn};`, context);
  await context.openHelpModal();

  assert.equal(modalCalls.length, 2);
  assert.equal(modalCalls[0].title, "Help");
  assert.match(modalCalls[0].htmlContent, /Loading help documentation/);

  assert.equal(modalCalls[1].title, "Help");
  assert.match(modalCalls[1].htmlContent, /^<p>network down<\/p>$/);
});

test("openHelpModal shows documentation link when README content is unavailable", async () => {
  const appJs = fs.readFileSync("pi_camera_in_docker/static/js/app.js", "utf8");
  const openHelpModalFn = extractFunction(appJs, "openHelpModal");

  const modalCalls = [];
  const context = {
    fetchReadmeContent: async () => ({
      status: "degraded",
      content: "",
      message: "README unavailable in container image",
      documentation_url: "https://github.com/CyanAutomation/motioninocean/blob/main/README.md",
      source: "github_fallback",
    }),
    openUtilityModal: (payload) => {
      modalCalls.push(payload);
    },
    escapeHtml: (value) => String(value),
  };

  vm.runInNewContext(`${openHelpModalFn};`, context);
  await context.openHelpModal();

  assert.equal(modalCalls.length, 2);
  assert.equal(modalCalls[1].title, "Help");
  assert.match(modalCalls[1].htmlContent, /README unavailable in container image/);
  assert.match(modalCalls[1].htmlContent, /href="https:\/\/github.com\/CyanAutomation\/motioninocean\/blob\/main\/README.md"/);
  assert.match(modalCalls[1].htmlContent, />Open documentation</);
});

test("openHelpModal sanitizes rendered markdown before showing help content", async () => {
  const appJs = fs.readFileSync("pi_camera_in_docker/static/js/app.js", "utf8");
  const openHelpModalFn = extractFunction(appJs, "openHelpModal");

  const modalCalls = [];
  const context = {
    fetchReadmeContent: async () => ({
      status: "ok",
      content: "# Help\n<script>alert(1)</script>\n<a href='https://example.com' onclick='evil()'>link</a>",
      message: "",
      documentation_url: "",
      source: "readme",
    }),
    renderMarkdownContent: () =>
      '<article><script>alert(1)</script><a href="https://example.com" onclick="evil()">safe</a></article>',
    sanitizeUtilityHtml: (html) =>
      html
        .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, "")
        .replace(/\son[a-z]+="[^"]*"/gi, ""),
    openUtilityModal: (payload) => {
      modalCalls.push(payload);
    },
    escapeHtml: (value) => String(value),
    console: {
      warn: () => {},
    },
  };

  vm.runInNewContext(`${openHelpModalFn};`, context);
  await context.openHelpModal();

  assert.equal(modalCalls.length, 2);
  assert.doesNotMatch(modalCalls[1].htmlContent, /<script/i);
  assert.doesNotMatch(modalCalls[1].htmlContent, /onclick=/i);
  assert.match(modalCalls[1].htmlContent, /href="https:\/\/example\.com"/);
});

test("openHelpModal falls back to escaped preformatted text when sanitization fails", async () => {
  const appJs = fs.readFileSync("pi_camera_in_docker/static/js/app.js", "utf8");
  const openHelpModalFn = extractFunction(appJs, "openHelpModal");

  const modalCalls = [];
  const context = {
    fetchReadmeContent: async () => ({
      status: "ok",
      content: "# Header\n<script>alert(1)</script>",
      message: "",
      documentation_url: "",
      source: "readme",
    }),
    renderMarkdownContent: () => "<article>unsafe html</article>",
    sanitizeUtilityHtml: () => {
      throw new Error("sanitizer failed");
    },
    openUtilityModal: (payload) => {
      modalCalls.push(payload);
    },
    escapeHtml: (value) => String(value).replace(/</g, "&lt;").replace(/>/g, "&gt;"),
    console: {
      warn: () => {},
    },
  };

  vm.runInNewContext(`${openHelpModalFn};`, context);
  await context.openHelpModal();

  assert.equal(modalCalls.length, 2);
  assert.match(modalCalls[1].htmlContent, /^<pre>/);
  assert.match(modalCalls[1].htmlContent, /&lt;script&gt;alert\(1\)&lt;\/script&gt;/);
});

test("sanitizeAnchorHref rejects unsafe protocols", () => {
  const appJs = fs.readFileSync("pi_camera_in_docker/static/js/app.js", "utf8");
  const sanitizeAnchorHrefFn = extractSyncFunction(appJs, "sanitizeAnchorHref");

  const context = {
    URL,
  };

  vm.runInNewContext(`${sanitizeAnchorHrefFn};`, context);

  assert.equal(context.sanitizeAnchorHref("https://example.com/docs"), "https://example.com/docs");
  assert.equal(context.sanitizeAnchorHref("/docs/help"), "/docs/help");
  assert.equal(context.sanitizeAnchorHref("javascript:alert(1)"), "");
  assert.equal(context.sanitizeAnchorHref("data:text/html,<script>alert(1)</script>"), "");
});
