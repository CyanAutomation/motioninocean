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

test("topbar mascot initializes and follows every supported tab", () => {
  const appJs = fs.readFileSync("pi_camera_in_docker/static/js/app.js", "utf8");
  const cacheElementsFn = extractFunction(appJs, "cacheElements");
  const getMioAssetsFn = extractFunction(appJs, "getMioAssets");
  const updateMascotForTabFn = extractFunction(appJs, "updateMascotForTab");

  const heroImage = { src: "", alt: "" };
  const elements = new Map([["mio-hero-image", heroImage]]);
  const context = {
    DEFAULT_MIO_PATH: "/static/img/mio/default.png",
    document: {
      body: {
        dataset: {
          mioAvatar: "/static/img/mio/mio_avatar.png",
          mioHappy: "/static/img/mio/mio_happy.png",
          mioCurious: "/static/img/mio/mio_curious.png",
          mioSleeping: "/static/img/mio/mio_sleeping.png",
          mioWinking: "/static/img/mio/mio_winking.png",
          mioFloating: "/static/img/mio/mio_floating.svg",
        },
      },
      getElementById(id) {
        return elements.get(id) ?? null;
      },
      querySelectorAll() {
        return [];
      },
    },
    state: {
      elements: {},
    },
  };

  vm.runInNewContext(`${cacheElementsFn}\n${getMioAssetsFn}\n${updateMascotForTabFn}`, context);

  assert.doesNotThrow(() => context.cacheElements());
  assert.equal(context.state.elements.mioHeroImage, heroImage);

  const tabExpectations = [
    ["main", "/static/img/mio/mio_happy.png", "Mio mascot for Stream view"],
    ["config", "/static/img/mio/mio_curious.png", "Mio mascot for Configuration view"],
    ["setup", "/static/img/mio/mio_avatar.png", "Mio mascot for Set-Up view"],
    ["settings", "/static/img/mio/mio_sleeping.png", "Mio mascot for Runtime Settings view"],
  ];

  for (const [tab, expectedSrc, expectedAlt] of tabExpectations) {
    assert.doesNotThrow(() => context.updateMascotForTab(tab));
    assert.equal(heroImage.src, expectedSrc);
    assert.equal(heroImage.alt, expectedAlt);
  }
});
