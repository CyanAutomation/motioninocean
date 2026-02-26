import { expect, test } from "@playwright/test";

test("changelog modal renders newest release first with full link", async ({ page }) => {
  await page.goto("/");

  await page.locator("#rail-changelog-btn").click();

  const modal = page.locator("#utility-modal");
  await expect(modal).toBeVisible();
  await expect(page.locator("#utility-modal-title")).toHaveText("Changelog");

  const cards = page.locator("#utility-modal-content .changelog-card");
  await expect(cards.first()).toBeVisible();

  const firstVersion = await cards.first().locator("h3").textContent();
  const secondVersion = await cards.nth(1).locator("h3").textContent();

  expect(firstVersion).toMatch(/^v\d+\.\d+\.\d+/);
  expect(secondVersion).toMatch(/^v\d+\.\d+\.\d+/);
  expect(firstVersion).not.toBe(secondVersion);

  await expect(page.locator('#utility-modal-content a[href="/docs/CHANGELOG.md"]')).toBeVisible();
});
