import { expect, test } from "@playwright/test";

const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 1024 },
  { name: "tablet", width: 1024, height: 768 },
  { name: "mobile", width: 390, height: 844 },
];

test("mock placeholder stays bounded within the video wrapper across viewports", async ({ page }) => {
  for (const viewport of VIEWPORTS) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");

    await page.waitForFunction(() => typeof window.applyMockStreamMode === "function");
    await page.evaluate(() => {
      window.applyMockStreamMode(true, false);
    });

    const wrapper = page.locator(".video-wrapper");
    const placeholder = page.locator("#mock-stream-placeholder");
    const animationHost = page.locator("#mock-stream-animation");

    await expect(wrapper).toBeVisible();
    await expect(placeholder).toBeVisible();
    await expect(animationHost).toBeVisible();

    const bounds = await page.evaluate(() => {
      const wrapperElement = document.querySelector(".video-wrapper");
      const placeholderElement = document.querySelector("#mock-stream-placeholder");
      const animationElement = document.querySelector("#mock-stream-animation");

      if (!wrapperElement || !placeholderElement || !animationElement) {
        return null;
      }

      const wrapperRect = wrapperElement.getBoundingClientRect();
      const placeholderRect = placeholderElement.getBoundingClientRect();
      const animationRect = animationElement.getBoundingClientRect();

      return {
        wrapperRect,
        placeholderRect,
        animationRect,
      };
    });

    expect(bounds, `missing bounds in ${viewport.name}`).not.toBeNull();

    const { wrapperRect, placeholderRect, animationRect } = bounds;
    expect(placeholderRect.width, `${viewport.name} placeholder width should fit wrapper`).toBeLessThanOrEqual(
      wrapperRect.width + 1,
    );
    expect(
      placeholderRect.height,
      `${viewport.name} placeholder height should fit wrapper`,
    ).toBeLessThanOrEqual(wrapperRect.height + 1);
    expect(animationRect.width, `${viewport.name} animation width should fit wrapper`).toBeLessThanOrEqual(
      wrapperRect.width + 1,
    );
    expect(
      animationRect.height,
      `${viewport.name} animation height should fit wrapper`,
    ).toBeLessThanOrEqual(wrapperRect.height + 1);

    await expect(placeholder).toHaveScreenshot(`webcam-mock-placeholder-${viewport.name}.png`);
  }
});
