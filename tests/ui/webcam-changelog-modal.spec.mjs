import { expect, test } from "@playwright/test";

test("changelog modal renders newest release first with API-provided full link", async ({ page }) => {
  const expectedFullChangelogUrl = "https://example.invalid/changelog";

  await page.route("**/api/changelog", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "ok",
        source_type: "remote",
        source: "/tmp/missing-local-changelog.md",
        entries: [
          {
            version: "2.0.0",
            release_date: "2025-01-03",
            changes: ["Added dynamic changelog URL support"],
          },
          {
            version: "1.9.0",
            release_date: "2024-12-20",
            changes: ["Improved modal rendering"],
          },
        ],
        full_changelog_url: expectedFullChangelogUrl,
      }),
    });
  });

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

  await expect(page.locator(`#utility-modal-content a[href="${expectedFullChangelogUrl}"]`)).toBeVisible();
  await expect(page.locator('#utility-modal-content a[href="/docs/CHANGELOG.md"]')).toHaveCount(0);
});

test("changelog modal hides full link and shows user-friendly degraded note when URL missing", async ({
  page,
}) => {
  await page.route("**/api/changelog", async (route) => {
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({
        status: "degraded",
        source_type: "remote",
        message: "Unable to read /app/docs/CHANGELOG.md",
        source: "/app/docs/CHANGELOG.md",
        full_changelog_url: "https://example.invalid/full-changelog",
        entries: [
          {
            version: "1.8.0",
            release_date: "2024-11-02",
            changes: ["Cached release card still available"],
          },
        ],
      }),
    });
  });

  await page.goto("/");
  await page.locator("#rail-changelog-btn").click();

  const modalContent = page.locator("#utility-modal-content");
  await expect(modalContent.locator(".changelog-card")).toBeVisible();
  await expect(modalContent.getByText("We couldn't load the latest changelog details right now.")).toBeVisible();
  await expect(modalContent.getByText("/app/docs/CHANGELOG.md")).toHaveCount(0);
  await expect(
    modalContent.getByRole("link", { name: "View full changelog" }),
  ).toHaveAttribute("href", "https://example.invalid/full-changelog");
  await expect(modalContent.locator('a[href="/docs/CHANGELOG.md"]')).toHaveCount(0);
});
