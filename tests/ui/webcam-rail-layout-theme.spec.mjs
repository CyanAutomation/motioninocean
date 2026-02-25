import { expect, test } from "@playwright/test";

const TAB_BUTTON_SELECTOR = ".webcam-side-rail .rail-primary-items .tab-btn";
const SIDE_RAIL_SELECTOR = ".webcam-side-rail";

function intersects(boxA, boxB) {
  return !(
    boxA.x + boxA.width <= boxB.x ||
    boxB.x + boxB.width <= boxA.x ||
    boxA.y + boxA.height <= boxB.y ||
    boxB.y + boxB.height <= boxA.y
  );
}

test("webcam side rail keeps tab buttons separated and updates theme colors", async ({ page }) => {
  await page.goto("/");

  const sideRail = page.locator(SIDE_RAIL_SELECTOR);
  await expect(sideRail).toBeVisible();

  const tabButtons = page.locator(TAB_BUTTON_SELECTOR);
  await expect(tabButtons).toHaveCount(4);

  const boxes = await tabButtons.evaluateAll((buttons) =>
    buttons.map((button) => {
      const box = button.getBoundingClientRect();
      return {
        label: button.textContent?.trim() || "",
        x: box.x,
        y: box.y,
        width: box.width,
        height: box.height,
      };
    }),
  );

  for (let i = 0; i < boxes.length; i += 1) {
    for (let j = i + 1; j < boxes.length; j += 1) {
      expect(
        intersects(boxes[i], boxes[j]),
        `Buttons overlap: \"${boxes[i].label}\" intersects \"${boxes[j].label}\"`,
      ).toBe(false);
    }
  }

  const readRailColors = () =>
    sideRail.evaluate((rail) => {
      const railStyle = window.getComputedStyle(rail);
      const firstInactiveButton = rail.querySelector(".tab-btn:not(.active)");
      const buttonStyle = firstInactiveButton ? window.getComputedStyle(firstInactiveButton) : null;
      return {
        railBackground: railStyle.backgroundColor,
        railBorder: railStyle.borderRightColor,
        buttonText: buttonStyle?.color ?? "",
      };
    });

  const lightColors = await readRailColors();
  expect(lightColors.railBackground).toBe("rgb(15, 23, 42)");

  await expect(sideRail).toHaveScreenshot("webcam-side-rail-light.png");

  await page.locator("#theme-toggle-btn").click();

  const darkColors = await readRailColors();
  expect(darkColors.railBackground).toBe("rgb(2, 6, 23)");
  expect(darkColors.railBorder).not.toBe(lightColors.railBorder);
  expect(darkColors.buttonText).not.toBe(lightColors.buttonText);

  await expect(sideRail).toHaveScreenshot("webcam-side-rail-dark.png");
});
