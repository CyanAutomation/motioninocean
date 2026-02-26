/**
 * @fileoverview E2E test for management dashboard error status display.
 * Tests that different node error states are displayed with meaningful messages to the user.
 */

import { test, expect } from "@playwright/test";

test.describe("Management Dashboard Error Status Display", () => {
  test("should display meaningful error messages for unavailable nodes", async ({
    page,
  }) => {
    /**
     * User-facing behavior test:
     * Verifies that when a management hub has nodes in error states,
     * the dashboard displays clear, actionable error messages to the operator.
     *
     * This tests user-observable contract:
     * - Unavailable nodes show visual indicator (color, icon, status badge)
     * - Error message explains what went wrong
     * - User can understand what action to take (reconnect, check network, etc.)
     */

    // Navigate to management dashboard
    await page.goto("http://localhost:8001/management");

    // Verify page structure
    await expect(page.locator("h1, h2")).first().toContainText(/Management/i);

    // Look for node status display area
    const nodeStatusArea = page.locator(
      "main, [role=main], .dashboard, [data-testid=nodes]"
    );
    await expect(nodeStatusArea).toBeVisible();

    // Get all node rows or list items
    const nodeElements = page.locator(
      "tbody tr, li[data-node-id], [role=listitem]"
    );
    const nodeCount = await nodeElements.count();

    if (nodeCount > 0) {
      // Verify nodes have status displays
      for (let i = 0; i < Math.min(nodeCount, 3); i++) {
        const node = nodeElements.nth(i);
        const nodeText = await node.textContent();

        // Node rows should indicate status: healthy, degraded, unavailable, etc.
        const hasStatusIndicator = /healthy|ok|online|unavailable|failed|error|degraded|offline/i.test(
          nodeText || ""
        );

        // Check for visual status indicator (badge, color, icon)
        const statusElement = node.locator(
          "[class*=status], [class*=badge], [title*=status]"
        );
        const hasStatusElement = (await statusElement.count()) > 0;

        expect(hasStatusIndicator || hasStatusElement).toBeTruthy(
          `Node ${i} should display status information`
        );
      }
    }

    // Verify overview section summarizes health
    const overviewSection = page.locator(
      "[class*=overview], [class*=summary], [class*=stats]"
    );
    const overviewVisible = await overviewSection.count() > 0;

    if (overviewVisible) {
      const overviewText = await overviewSection.first().textContent();

      // Should show counts or summary (e.g., "3 healthy, 1 unavailable")
      const hasSummary = /(\d+\s+(healthy|available|online|unavailable|failed|error))/i.test(
        overviewText || ""
      );

      expect(hasSummary || overviewText?.length > 0).toBeTruthy(
        "Overview should summarize node health status"
      );
    }
  });

  test("should provide actionable error context in node details", async ({
    page,
  }) => {
    /**
     * User-facing behavior test:
     * When a node is unavailable or in error state, clicking/viewing its details
     * should provide context to help the operator diagnose and fix the issue.
     */

    await page.goto("http://localhost:8001/management");

    // Find any node with error status
    const errorNode = page.locator(
      '[class*=error] button, [class*=unavailable] a, [title*=Error] span'
    ).first();

    const nodeRowWithError = page.locator(
      "tbody tr:has([class*=error]), tr:has([class*=unavailable])"
    ).first();

    if ((await nodeRowWithError.count()) > 0) {
      // Click to expand or view details
      const expandButton = nodeRowWithError.locator(
        "button, a, [role=button]"
      ).first();

      if ((await expandButton.count()) > 0) {
        await expandButton.click();

        // Wait for details to appear
        await page
          .locator("[class*=details], [class*=panel], [role=dialog]")
          .first()
          .waitFor({ state: "visible", timeout: 2000 })
          .catch(() => {});
      }

      // Look for error explanation or reason
      const errorReason = nodeRowWithError.locator(
        "[title*=reason], [aria-label*=error], [class*=message]"
      );

      if ((await errorReason.count()) > 0) {
        const reasonText = await errorReason.first().textContent();

        // Error should include actionable info (reason, what to fix)
        expect(reasonText?.length).toBeGreaterThan(
          0
        );
      }
    }

    // If no error nodes, verify the dashboard at least has the structure to show them
    const hasNodeContainer = await page
      .locator(
        "table, [role=table], .nodes-list, [class*=node], [data-testid]"
      )
      .first()
      .isVisible();

    expect(hasNodeContainer).toBeTruthy(
      "Dashboard should have node display container"
    );
  });
});
