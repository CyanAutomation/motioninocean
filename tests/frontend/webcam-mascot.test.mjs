import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

function extractFunction(source, functionName) {
  const match = source.match(
    new RegExp(`function ${functionName}\\([^)]*\\) \\{[\\s\\S]*?\\n^}`, "m"),
  );
  if (!match) {
    throw new Error(`${functionName}() definition not found`);
  }
  return match[0];
}

test("updateMascotForTab updates only topbar hero mascot image", () => {
  const appJs = fs.readFileSync("pi_camera_in_docker/static/js/app.js", "utf8");
  const getMioAssetsFn = extractFunction(appJs, "getMioAssets");
  const updateMascotForTabFn = extractFunction(appJs, "updateMascotForTab");

  const heroImage = { src: "", alt: "" };
  const context = {
    DEFAULT_MIO_PATH: "/static/img/mio/default.png",
    document: {
      body: {
        dataset: {
          mioAvatar: "/static/img/mio/mio_avatar.png",
          mioHappy: "/static/img/mio/mio_happy.png",
          mioCurious: "/static/img/mio/mio_curious.png",
          mioSleeping: "/static/img/mio/mio_sleeping.png",
        },
      },
    },
    state: {
      elements: {
        mioHeroImage: heroImage,
      },
    },
  };

  vm.runInNewContext(`${getMioAssetsFn}\n${updateMascotForTabFn}`, context);

  context.updateMascotForTab("config");
  assert.equal(heroImage.src, "/static/img/mio/mio_curious.png");
  assert.equal(heroImage.alt, "Mio mascot for Configuration view");

  context.updateMascotForTab("unknown-tab");
  assert.equal(heroImage.src, "/static/img/mio/mio_happy.png");
  assert.equal(heroImage.alt, "Mio mascot for Stream view");
});

test("app.js no longer references removed context mascot DOM ids", () => {
  const appJs = fs.readFileSync("pi_camera_in_docker/static/js/app.js", "utf8");

  assert.equal(appJs.includes("mio-stream-image"), false);
  assert.equal(appJs.includes("mio-config-image"), false);
  assert.equal(appJs.includes("mio-setup-image"), false);
  assert.equal(appJs.includes("mio-settings-image"), false);
});
