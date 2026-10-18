import test from "node:test";
import assert from "node:assert/strict";
import {
  updateMioMascotForTab,
  type MioMascotAssets,
} from "../../frontend/src/mio-mascot.ts";

test("mascot image and accessible label follow the active viewer tab", () => {
  const assets: MioMascotAssets = {
    avatar: "/static/img/mio/mio_avatar.png",
    curious: "/static/img/mio/mio_curious.png",
    floating: "/static/img/mio/mio_floating.svg",
    happy: "/static/img/mio/mio_happy.png",
    sleeping: "/static/img/mio/mio_sleeping.png",
    winking: "/static/img/mio/mio_winking.png",
  };

  const tabExpectations = [
    ["main", assets.happy, "Mio mascot for Stream view"],
    ["config", assets.curious, "Mio mascot for Configuration view"],
    ["setup", assets.avatar, "Mio mascot for Set-Up view"],
    ["settings", assets.sleeping, "Mio mascot for Runtime Settings view"],
  ] as const;
  const heroImage = { src: "", alt: "" };

  for (const [tab, src, alt] of tabExpectations) {
    updateMioMascotForTab(tab, heroImage, assets);
    assert.equal(heroImage.src, src);
    assert.equal(heroImage.alt, alt);
  }

  updateMioMascotForTab("unknown", heroImage, assets);
  assert.equal(heroImage.src, assets.happy);
  assert.equal(heroImage.alt, "Mio mascot for Stream view");
  assert.doesNotThrow(() => updateMioMascotForTab("main", null, assets));
});
