import { expect, test } from "@playwright/test";

async function assertUtilityModalGeometry(page) {
  const geometry = await page.locator("#utility-modal").evaluate((element) => {
    const style = window.getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return {
      position: style.position,
      zIndex: Number.parseInt(style.zIndex || "0", 10),
      rect: {
        top: rect.top,
        left: rect.left,
        width: rect.width,
        height: rect.height,
      },
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight,
      },
    };
  });

  expect(geometry.position).toBe("fixed");
  expect(geometry.zIndex).toBeGreaterThanOrEqual(100);
  expect(geometry.rect.width).toBeGreaterThan(0);
  expect(geometry.rect.height).toBeGreaterThan(0);
  expect(geometry.rect.left).toBeGreaterThanOrEqual(0);
  expect(geometry.rect.top).toBeGreaterThanOrEqual(0);
  expect(geometry.rect.left).toBeLessThanOrEqual(32);
  expect(geometry.rect.top).toBeLessThanOrEqual(24);
  expect(geometry.rect.width).toBeGreaterThanOrEqual(geometry.viewport.width - 64);
  expect(geometry.rect.height).toBeGreaterThanOrEqual(geometry.viewport.height - 64);

  const panelRect = await page.locator("#utility-modal .utility-modal__panel").boundingBox();
  expect(panelRect).not.toBeNull();
  expect(panelRect.x).toBeGreaterThanOrEqual(0);
  expect(panelRect.y).toBeGreaterThanOrEqual(0);
  expect(panelRect.x + panelRect.width).toBeLessThanOrEqual(geometry.viewport.width);
  expect(panelRect.y + panelRect.height).toBeLessThanOrEqual(geometry.viewport.height);

  const railRect = await page.locator(".webcam-side-rail").boundingBox();
  if (railRect && railRect.width > 0 && railRect.height > 0) {
    expect(panelRect.x).toBeGreaterThanOrEqual(railRect.x + railRect.width - 1);
  }
}

test("help modal opens and shows scrollable README content", async ({ page }) => {
  await page.goto("/");

  await page.locator("#rail-help-btn").click();

  const modal = page.locator("#utility-modal");
  const title = page.locator("#utility-modal-title");
  const readmeContent = page.locator("#utility-modal-content .utility-modal__readme");

  await expect(modal).toBeVisible();
  await assertUtilityModalGeometry(page);
  await expect(title).toHaveText("Help");
  await expect(readmeContent).toBeVisible();

  const overflowY = await readmeContent.evaluate(
    (element) => window.getComputedStyle(element).overflowY,
  );
  expect(["auto", "scroll"]).toContain(overflowY);
});
