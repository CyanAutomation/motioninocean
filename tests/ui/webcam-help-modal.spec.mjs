import { expect, test } from "@playwright/test";

test("help modal opens and shows scrollable README content", async ({ page }) => {
  await page.goto("/");

  await page.locator("#rail-help-btn").click();

  const modal = page.locator("#utility-modal");
  const title = page.locator("#utility-modal-title");
  const readmeContent = page.locator("#utility-modal-content .utility-modal__readme");

  await expect(modal).toBeVisible();
  await expect(title).toHaveText("Help");
  await expect(readmeContent).toBeVisible();

  const overflowY = await readmeContent.evaluate(
    (element) => window.getComputedStyle(element).overflowY,
  );
  expect(["auto", "scroll"]).toContain(overflowY);
});
