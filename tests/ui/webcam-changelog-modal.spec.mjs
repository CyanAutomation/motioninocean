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
  if (panelRect) {
    expect(panelRect.x).toBeGreaterThanOrEqual(0);
    expect(panelRect.y).toBeGreaterThanOrEqual(0);
    expect(panelRect.x + panelRect.width).toBeLessThanOrEqual(geometry.viewport.width);
    expect(panelRect.y + panelRect.height).toBeLessThanOrEqual(geometry.viewport.height);
  }

  const railRect = await page.locator(".webcam-side-rail").boundingBox();
  if (railRect && railRect.width > 0 && railRect.height > 0) {
    expect(panelRect.x).toBeGreaterThanOrEqual(railRect.x + railRect.width - 1);
  }
}
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
  await assertUtilityModalGeometry(page);
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

  await assertUtilityModalGeometry(page);
  const modalContent = page.locator("#utility-modal-content");
  await expect(modalContent.locator(".changelog-card")).toBeVisible();
  await expect(modalContent.getByText("We couldn't load the latest changelog details right now.")).toBeVisible();
  await expect(modalContent.getByText("/app/docs/CHANGELOG.md")).toHaveCount(0);
  await expect(
    modalContent.getByRole("link", { name: "View full changelog" }),
  ).toHaveAttribute("href", "https://example.invalid/full-changelog");
  await expect(modalContent.locator('a[href="/docs/CHANGELOG.md"]')).toHaveCount(0);
});
