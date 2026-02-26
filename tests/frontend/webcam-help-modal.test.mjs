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
  assert.match(modalCalls[1].htmlContent, /Unable to load help documentation: network down/);
});
