#!/usr/bin/env node

/**
 * Motion-in-Ocean UI Audit Template
 *
 * This script provides a template for AI agents to perform systematic UI audits
 * of motion-in-ocean's web interfaces using Playwright.
 *
 * Prerequisites:
 * - npm install (or npx playwright install)
 * - Motion-in-Ocean server running (local or Docker)
 * - Environment: MOCK_CAMERA=true for mock mode
 *
 * Usage:
 * node audit-template.js [--mode webcam|management|both] [--url http://localhost:8000]
 */

const { chromium } = require("@playwright/test");
const fs = require("fs");
const path = require("path");

const AUDIT_CONFIG = {
  baseUrl: process.env.MIO_URL || "http://localhost:8000",
  mode: process.env.MIO_MODE || "both", // webcam, management, or both
  outputDir: "./audit-results",
  viewports: {
    desktop: { name: "desktop", width: 1280, height: 720 },
    tablet: { name: "tablet", width: 768, height: 1024 },
    mobile: { name: "mobile", width: 375, height: 667 },
  },
};

// ============================================================================
// AUDIT HELPERS
// ============================================================================

async function capturePageState(page, baseFilename) {
  const state = await page.evaluate(() => ({
    title: document.title,
    url: window.location.href,
    viewport: { width: window.innerWidth, height: window.innerHeight },
    hasErrors: document.querySelectorAll('.error, [role="alert"]').length,
    visibleElements: {
      header: !!document.querySelector(".header"),
      video: !!document.querySelector(".video-container"),
      stats: !!document.querySelector("#stats-panel"),
      form: !!document.querySelector("#node-form"),
      table: !!document.querySelector("#nodes-table-body"),
    },
  }));

  await page.screenshot({ path: path.join(AUDIT_CONFIG.outputDir, `${baseFilename}.png`) });
  return state;
}

async function testResponsiveDesign(page, baseFilename) {
  console.log(`  Testing responsive design...`);
  const results = {};

  for (const [_, viewport] of Object.entries(AUDIT_CONFIG.viewports)) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.waitForLoadState("networkidle");

    const state = await capturePageState(page, `${baseFilename}-${viewport.name}`);
    results[viewport.name] = state;

    console.log(`    ✓ ${viewport.name} (${viewport.width}×${viewport.height})`);
  }

  return results;
}

async function checkAccessibility(page) {
  console.log(`  Checking accessibility...`);

  const a11yIssues = await page.evaluate(() => {
    const issues = [];

    // Check for images without alt text
    document.querySelectorAll("img:not([alt])").forEach((img, i) => {
      issues.push(`Image ${i} missing alt text`);
    });

    // Check for missing form labels
    document.querySelectorAll("input, select, textarea").forEach((input) => {
      const label = document.querySelector(`label[for="${input.id}"]`);
      if (!label && !input.getAttribute("aria-label")) {
        issues.push(`Input ${input.id || input.name} missing associated label`);
      }
    });

    // Check for focus outline visibility
    const buttons = document.querySelectorAll("button");
    if (buttons.length > 0) {
      const firstButton = buttons[0];
      const _styles = window.getComputedStyle(firstButton, ":focus");
      // Note: Can't directly check :focus pseudo-class, but can verify no outline:0
      if (firstButton.style.outline === "none" || firstButton.style.outline === "0") {
        issues.push("Buttons may have focus outline disabled");
      }
    }

    return issues;
  });

  a11yIssues.forEach((issue) => {
    console.log(`    ! ${issue}`);
  });

  return a11yIssues;
}

// ============================================================================
// WEBCAM MODE AUDIT
// ============================================================================

async function auditWebcamMode(page) {
  console.log("\n📺 WEBCAM MODE AUDIT");
  console.log("─".repeat(50));

  const findings = {
    layout: [],
    responsive: {},
    accessibility: [],
    errors: [],
  };

  try {
    // Initial load
    console.log("\n1. Page Load");
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto(`${AUDIT_CONFIG.baseUrl}`, { waitUntil: "networkidle" });

    const initialState = await capturePageState(page, "webcam-initial");
    console.log("  ✓ Initial state captured");
    console.log(`    URL: ${initialState.url}`);
    console.log(`    Title: ${initialState.title}`);

    // Check for errors
    if (initialState.hasErrors > 0) {
      findings.errors.push(`Page has ${initialState.hasErrors} error elements`);
    }

    // Layout inspection
    console.log("\n2. Layout Inspection");
    const headerExists = await page.locator(".header").isVisible();
    const videoExists = await page.locator(".video-container").isVisible();
    const statsExists = await page.locator("#stats-panel").isVisible();

    console.log(`  ${headerExists ? "✓" : "✗"} Header visible`);
    console.log(`  ${videoExists ? "✓" : "✗"} Video container visible`);
    console.log(`  ${statsExists ? "✓" : "✗"} Stats panel visible`);

    if (!headerExists) findings.layout.push("Header not visible on initial load");
    if (!videoExists) findings.layout.push("Video container not visible");

    // Responsive design
    console.log("\n3. Responsive Design");
    findings.responsive = await testResponsiveDesign(page, "webcam");

    // Accessibility
    console.log("\n4. Accessibility");
    findings.accessibility = await checkAccessibility(page);

    // Stream interaction (wait for video to load)
    console.log("\n5. Stream Interaction");
    try {
      await page.waitForSelector("img#video-stream", { timeout: 5000 });
      const _videoState = await capturePageState(page, "webcam-streaming");
      console.log("  ✓ Video stream loaded");
    } catch (_e) {
      findings.errors.push("Video stream did not load within 5 seconds");
      console.log("  ! Video stream timeout or not loaded");
    }

    // Tab switching
    console.log("\n6. Tab Navigation");
    const configTabButton = await page.locator('button[data-tab="config"]').isVisible();
    if (configTabButton) {
      await page.click('button[data-tab="config"]');
      await page.waitForTimeout(500);
      await capturePageState(page, "webcam-config-tab");
      console.log("  ✓ Config tab loads");

      await page.click('button[data-tab="main"]');
      await page.waitForTimeout(500);
      console.log("  ✓ Back to main tab");
    }
  } catch (error) {
    findings.errors.push(`Audit error: ${error.message}`);
    console.error(`  ✗ Error: ${error.message}`);
  }

  return findings;
}

// ============================================================================
// MANAGEMENT MODE AUDIT
// ============================================================================

async function auditManagementMode(page) {
  console.log("\n🎛️  MANAGEMENT MODE AUDIT");
  console.log("─".repeat(50));

  const findings = {
    layout: [],
    responsive: {},
    accessibility: [],
    errors: [],
    nodeOps: [],
  };

  try {
    // Navigate to management mode (usually port 8001 or /management path)
    const mgmtUrl = AUDIT_CONFIG.baseUrl.replace(":8000", ":8001");

    console.log("\n1. Page Load");
    await page.setViewportSize({ width: 1280, height: 720 });

    // Try management port first, fall back to path
    try {
      await page.goto(mgmtUrl, { waitUntil: "networkidle" });
    } catch {
      await page.goto(`${AUDIT_CONFIG.baseUrl}/management`, { waitUntil: "networkidle" });
    }

    const initialState = await capturePageState(page, "management-initial");
    console.log("  ✓ Initial state captured");
    console.log(`    URL: ${initialState.url}`);

    // Layout inspection
    console.log("\n2. Layout Inspection");
    const formExists = await page.locator("#node-form").isVisible();
    const tableExists = await page.locator("#nodes-table-body").isVisible();

    console.log(`  ${formExists ? "✓" : "✗"} Node form visible`);
    console.log(`  ${tableExists ? "✓" : "✗"} Node table visible`);

    if (!formExists) findings.layout.push("Node form not visible");
    if (!tableExists) findings.layout.push("Node table not visible");

    // Responsive design
    console.log("\n3. Responsive Design");
    findings.responsive = await testResponsiveDesign(page, "management");

    // Accessibility
    console.log("\n4. Accessibility");
    findings.accessibility = await checkAccessibility(page);

    // Form validation
    console.log("\n5. Form Validation");
    if (formExists) {
      // Check form labels
      const labels = await page.locator("#node-form label").count();
      console.log(`  Forms detected: ${labels} labels found`);

      // Try submitting empty form
      const submitButton = await page.locator('#node-form button[type="submit"]');
      if (await submitButton.isVisible()) {
        await submitButton.click();
        await page.waitForTimeout(500);

        const feedback = await page
          .locator("#form-feedback")
          .innerText()
          .catch(() => "");
        if (feedback) {
          console.log(`  ✓ Form validation feedback: "${feedback}"`);
          findings.nodeOps.push("Form validation working");
        }
      }
    }

    // Node list behavior
    console.log("\n6. Node List Behavior");
    if (tableExists) {
      const nodeCount = await page.locator("#nodes-table-body tr").count();
      console.log(`  Nodes visible: ${nodeCount}`);

      if (nodeCount === 0) {
        const emptyMsg = await page
          .locator(".empty-state-message")
          .innerText()
          .catch(() => "");
        console.log(`  Empty state: "${emptyMsg}"`);
      }

      // Check status pills
      const statusPills = await page.locator('[class*="status-"]').count();
      console.log(`  Status indicators: ${statusPills} found`);
    }
  } catch (error) {
    findings.errors.push(`Audit error: ${error.message}`);
    console.error(`  ✗ Error: ${error.message}`);
  }

  return findings;
}

// ============================================================================
// REPORT GENERATION
// ============================================================================

function generateReport(webcamFindings, managementFindings) {
  const timestamp = new Date().toISOString();

  let report = `# Motion-in-Ocean UI Audit Report\n\n`;
  report += `**Timestamp:** ${timestamp}\n`;
  report += `**Base URL:** ${AUDIT_CONFIG.baseUrl}\n`;
  report += `**Output Directory:** ${AUDIT_CONFIG.outputDir}\n\n`;

  if (AUDIT_CONFIG.mode === "webcam" || AUDIT_CONFIG.mode === "both") {
    report += `## Webcam Mode\n\n`;
    report += `**Layout Issues:** ${webcamFindings.layout.length}\n`;
    webcamFindings.layout.forEach((issue) => {
      report += `- ${issue}\n`;
    });
    report += `\n**Accessibility Issues:** ${webcamFindings.accessibility.length}\n`;
    webcamFindings.accessibility.forEach((issue) => {
      report += `- ${issue}\n`;
    });
    report += `\n**Errors:** ${webcamFindings.errors.length}\n`;
    webcamFindings.errors.forEach((issue) => {
      report += `- ${issue}\n`;
    });
    report += "\n";
  }

  if (AUDIT_CONFIG.mode === "management" || AUDIT_CONFIG.mode === "both") {
    report += `## Management Mode\n\n`;
    report += `**Layout Issues:** ${managementFindings.layout.length}\n`;
    managementFindings.layout.forEach((issue) => {
      report += `- ${issue}\n`;
    });
    report += `\n**Accessibility Issues:** ${managementFindings.accessibility.length}\n`;
    managementFindings.accessibility.forEach((issue) => {
      report += `- ${issue}\n`;
    });
    report += `\n**Errors:** ${managementFindings.errors.length}\n`;
    managementFindings.errors.forEach((issue) => {
      report += `- ${issue}\n`;
    });
    report += "\n";
  }

  report += `## Summary\n\n`;
  const totalIssues =
    (webcamFindings.layout.length || 0) +
    (webcamFindings.accessibility.length || 0) +
    (managementFindings.layout.length || 0) +
    (managementFindings.accessibility.length || 0);
  report += `**Total Issues Found:** ${totalIssues}\n`;

  return report;
}

// ============================================================================
// MAIN EXECUTION
// ============================================================================

async function main() {
  console.log("🔍 Motion-in-Ocean UI Audit");
  console.log("═".repeat(50));

  // Ensure output directory exists
  if (!fs.existsSync(AUDIT_CONFIG.outputDir)) {
    fs.mkdirSync(AUDIT_CONFIG.outputDir, { recursive: true });
  }

  let browser;
  try {
    browser = await chromium.launch();
    const page = await browser.newPage();

    let webcamFindings = {};
    let managementFindings = {};

    if (AUDIT_CONFIG.mode === "webcam" || AUDIT_CONFIG.mode === "both") {
      webcamFindings = await auditWebcamMode(page);
    }

    if (AUDIT_CONFIG.mode === "management" || AUDIT_CONFIG.mode === "both") {
      managementFindings = await auditManagementMode(page);
    }

    // Generate report
    const report = generateReport(webcamFindings, managementFindings);
    const reportPath = path.join(AUDIT_CONFIG.outputDir, "UI-AUDIT-REPORT.md");
    fs.writeFileSync(reportPath, report);

    console.log("\n✅ Audit Complete");
    console.log(`📄 Report written to: ${reportPath}`);
    console.log(`📸 Screenshots saved to: ${AUDIT_CONFIG.outputDir}`);
  } catch (error) {
    console.error("❌ Audit failed:", error);
    process.exit(1);
  } finally {
    if (browser) {
      await browser.close();
    }
  }
}

main();
