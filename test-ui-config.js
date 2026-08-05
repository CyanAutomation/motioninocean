#!/usr/bin/env node

import { chromium } from "playwright";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SCREENSHOTS_DIR = path.resolve(__dirname, "audit-results/config-tab/screenshots");
const REPORT_FILE = path.resolve(
  __dirname,
  "audit-results/config-tab/CONFIG_TAB_USABILITY_REPORT.md",
);
const VIEWPORTS = {
  desktop: { width: 1280, height: 720, name: "Desktop" },
  tablet: { width: 768, height: 1024, name: "Tablet" },
  mobile: { width: 375, height: 667, name: "Mobile" },
};

function createFindings() {
  return {
    general: [],
    desktop: [],
    tablet: [],
    mobile: [],
    interactivity: [],
    accessibility: [],
    issues: [],
  };
}

async function getConfigViewportMetrics(page) {
  return page.evaluate(() => {
    const element = document.querySelector(".config-content");
    return {
      width: document.documentElement.clientWidth,
      overflow: element ? element.scrollWidth > element.clientWidth : false,
    };
  });
}

async function getMinimumConfigFontSize(page) {
  const sizes = await page.evaluate(() =>
    Array.from(document.querySelectorAll(".config-label, .config-value")).map((element) =>
      parseFloat(window.getComputedStyle(element).fontSize),
    ),
  );
  return sizes.length ? Math.min(...sizes) : 0;
}

async function takeAndLogScreenshot(page, report, name, description) {
  const filename = `${name}.png`;
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, filename), fullPage: false });
  report.push({ filename, name, description });
  console.log(`✓ Screenshot: ${filename}`);
}

async function inspectGeneral(page, findings, screenshots) {
  const configGroups = await page.locator("[data-group]").count();
  findings.general.push({
    status: "✓",
    test: "Config groups found",
    details: `Found ${configGroups} collapsible config groups`,
  });

  for (const [label, test] of [
    ["📷 Camera Settings", "Camera Settings section"],
    ["📡 Stream Control", "Stream Control section"],
    ["⚙️ Runtime Information", "Runtime Information section"],
  ]) {
    const found = (await page.locator(`text=${label}`).count()) > 0;
    findings.general.push({
      status: found ? "✓" : "⚠",
      test,
      details: `${test} ${found ? "found" : "NOT FOUND"}`,
    });
  }

  const configItems = await page.locator(".config-item").count();
  findings.general.push({
    status: "✓",
    test: "Config items displayed",
    details: `Found ${configItems} configuration items`,
  });
  const configValues = await page.locator('[data-config-value="true"]').allTextContents();
  findings.general.push({
    status: configValues.some((value) => value && value !== "--") ? "✓" : "⚠",
    test: "Config values populated",
    details: configValues.some((value) => value && value !== "--")
      ? "Configuration values are being populated from the API"
      : "All config values appear to be placeholders (--)",
  });
  await takeAndLogScreenshot(
    page,
    screenshots,
    "desktop-03-config-expanded",
    "Config tab with all sections expanded (desktop)",
  );
}

async function inspectInteractivity(page, findings) {
  const toggleButtons = await page.locator(".config-group-toggle").count();
  findings.interactivity.push({
    status: toggleButtons === 0 ? "✓" : "⚠",
    test: toggleButtons === 0 ? "No collapse toggle buttons" : "Unexpected toggle buttons",
    details:
      toggleButtons === 0
        ? "Config sections are permanently expanded — no toggle buttons present"
        : `Found ${toggleButtons} toggle button(s)`,
  });
  const sections = await page.locator(".config-group-content").all();
  const allVisible = (await Promise.all(sections.map((section) => section.isVisible()))).every(
    Boolean,
  );
  findings.interactivity.push({
    status: allVisible ? "✓" : "⚠",
    test: "Config sections always visible",
    details: allVisible
      ? `All ${sections.length} config sections are permanently expanded`
      : "One or more config sections are hidden unexpectedly",
  });
}

async function inspectResponsive(page, findings, screenshots) {
  for (const [name, viewport, bucket] of [
    ["tablet", VIEWPORTS.tablet, "tablet"],
    ["mobile", VIEWPORTS.mobile, "mobile"],
  ]) {
    await page.setViewportSize(viewport);
    await page.waitForTimeout(500);
    await takeAndLogScreenshot(
      page,
      screenshots,
      `${name}-01-config-tab`,
      `Config tab on ${viewport.name}`,
    );
    const metrics = await getConfigViewportMetrics(page);
    findings[bucket].push({
      status: metrics.overflow ? "⚠" : "✓",
      test: "No horizontal scroll",
      details: `Viewport width: ${metrics.width}px. Horizontal overflow: ${metrics.overflow ? "YES - Issue!" : "NO"}`,
    });
    if (name === "mobile") {
      const minFont = await getMinimumConfigFontSize(page);
      findings.mobile.push({
        status: minFont >= 12 ? "✓" : "⚠",
        test: "Font size readability",
        details: `Minimum font size: ${minFont}px (should be >= 12px for readability)`,
      });
    }
  }
  await page.setViewportSize(VIEWPORTS.desktop);
}

async function inspectAccessibility(page, findings, screenshots) {
  const ariaLabels = await page.locator("[aria-label], [aria-labelledby]").count();
  findings.accessibility.push({
    status: ariaLabels > 0 ? "✓" : "⚠",
    test: "ARIA labels present",
    details: `Found ${ariaLabels} elements with ARIA labels`,
  });
  await page.keyboard.press("Tab");
  const focusedElement = await page.evaluate(() => document.activeElement?.tagName || "NONE");
  findings.accessibility.push({
    status: focusedElement !== "BODY" ? "✓" : "⚠",
    test: "Keyboard focus visible",
    details: `Focused element: ${focusedElement}`,
  });
  for (let index = 0; index < 5; index += 1) await page.keyboard.press("Tab");
  await takeAndLogScreenshot(
    page,
    screenshots,
    "desktop-04-keyboard-focus",
    "Keyboard focus state on config controls",
  );
}

function writeReport(findings, screenshots) {
  const table = (rows) =>
    rows.map((row) => `| ${row.test} | ${row.status} | ${row.details} |`).join("\n");
  const content = `# Config Tab Usability Report
Generated: ${new Date().toISOString()}

## Executive Summary

The Config tab was checked for structure, data population, responsive layout, accessibility, and keyboard navigation.

## General Findings
| Finding | Status | Details |
|---------|--------|---------|
${table(findings.general)}

## Interactivity
| Finding | Status | Details |
|---------|--------|---------|
${table(findings.interactivity)}

## Responsive Design
| Finding | Status | Details |
|---------|--------|---------|
${table([...findings.tablet, ...findings.mobile])}

## Accessibility
| Finding | Status | Details |
|---------|--------|---------|
${table(findings.accessibility)}

## Screenshots
${screenshots.map((item) => `- \`${item.filename}\`: ${item.description}`).join("\n")}
`;
  fs.writeFileSync(REPORT_FILE, content);
  console.log(`📄 Report written to: ${REPORT_FILE}`);
}

async function runTest() {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
  fs.mkdirSync(path.dirname(REPORT_FILE), { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: VIEWPORTS.desktop });
  const findings = createFindings();
  const screenshots = [];

  try {
    console.log("🚀 Starting Config Tab UI Test\n");
    await page.goto("http://localhost:8000", { waitUntil: "networkidle" });
    await page.waitForTimeout(2000);
    await takeAndLogScreenshot(
      page,
      screenshots,
      "desktop-01-stream-tab",
      "Initial Stream tab (desktop)",
    );
    await page.click('button[data-tab="config"]');
    await page.waitForTimeout(500);
    await takeAndLogScreenshot(
      page,
      screenshots,
      "desktop-02-config-tab-initial",
      "Config tab initial state (desktop)",
    );
    await inspectGeneral(page, findings, screenshots);
    await inspectInteractivity(page, findings);
    await inspectResponsive(page, findings, screenshots);
    await inspectAccessibility(page, findings, screenshots);
    writeReport(findings, screenshots);
    console.log("✅ Test complete");
  } finally {
    await browser.close();
    console.log("✅ Browser closed");
  }
}

runTest().catch((error) => {
  console.error("❌ Test failed:", error);
  process.exitCode = 1;
});
