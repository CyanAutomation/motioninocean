---
name: ui-playwright
description: Audit motion-in-ocean web UI (streaming viewer & node management) using Playwright; inspect layout, UX flows, accessibility, responsive design, and error handling.
---

# Skill: UI Auditing with Playwright for motion-in-ocean

## Purpose

Enable AI agents to systematically inspect and evaluate the motion-in-ocean web UI across both application modes (webcam streaming viewer and management node interface). Agents capture UI state, validate workflows, inspect responsive design, check accessibility compliance, and identify UX/design issues. This skill is **exploratory auditing** (evaluation/inspection) rather than automated testing (verification/regression).

---

## Inputs / Outputs / Non-goals

- **Inputs:** Running motion-in-ocean instance (local Docker, mock camera mode), Playwright browser automation, UI specification (PRD-frontend.md), accessibility/responsive design standards.
- **Outputs:** Structured UI audit report (markdown with screenshots/evidence), findings on layout, UX flows, accessibility, responsive behavior, error handling, interaction patterns.
- **Non-goals:** Writing test code or assertions, catching regressions automatically, validating API correctness, performance benchmarking.

---

## Trigger Conditions

Use this skill when:

- Performing design QA before PR merge (UI changes, component updates).
- Validating responsive layout across device sizes (mobile, tablet, desktop).
- Checking accessibility compliance (ARIA labels, keyboard navigation, color contrast).
- Exploring error scenarios and edge cases (stream failures, network timeouts, validation errors).
- Auditing UX flows end-to-end (stream viewing, node management, tab switching, form submission).
- Evaluating consistency of design tokens (colors, spacing, typography, button states).
- Documenting UI behavior changes for release notes or design updates.

---

## Mandatory Rules

1. **Inspect both modes:** Audit workflows include both **webcam mode** (streaming viewer) and **management mode** (node registry interface). Don't skip either.

2. **Responsive-first approach:** Always test at three viewports:
   - **Desktop:** 1280×720 (viewport width > 1024px)
   - **Tablet:** 768×1024 (viewport width 768-1024px)
   - **Mobile:** 375×667 (viewport width < 480px)
   - Note: Breakpoints align with CSS in `pi_camera_in_docker/static/css/style.css` and `management.css`

3. **Capture evidence:** Every finding includes **screenshot or state dump** showing the issue. Use Playwright's `page.screenshot()` at each viewport.

4. **UX workflow focus:** Audit user journeys end-to-end, not isolated clicks. Examples:
   - **Webcam:** Load page → stream appears → controls visible → stats update → tab switch
   - **Management:** List loads → add node → success feedback → table updates → edit/delete

5. **Accessibility as first-class:** Check compliance with WCAG 2.1 Level AA minimum. Include ARIA labels, color contrast, keyboard navigation, focus states, form labels.

6. **Error state exploration:** Don't just test happy paths. Systematically explore failures: network errors, validation failures, stale streams, missing data.

7. **Deterministic findings:** Observations must be reproducible and specific. Instead of "looks bad," report: "Button text 'Submit' is cut off at 375px width because it has 12px padding on 24px button height."

8. **Mock data when needed:** Use mock camera mode (`MOCK_CAMERA=true`) for consistent, fast UI testing without hardware.

---

## Context: motion-in-ocean UI Structure

### Webcam Mode (`/` - index.html)

**Key Elements:**

| Element          | Selector                                    | Purpose                                           |
| ---------------- | ------------------------------------------- | ------------------------------------------------- |
| Header           | `.header`                                   | Sticky, contains logo, tabs, connection status    |
| Video Container  | `.video-container`                          | 4:3 aspect ratio, holds stream video feed         |
| Video Stream     | `img#video-stream`                          | MJPEG stream image                                |
| Loading Overlay  | `.loading-overlay`                          | Spinner visible while stream loads                |
| Video Controls   | `.video-controls`                           | Refresh, fullscreen, play buttons                 |
| Status Indicator | `.status-indicator`                         | Pill showing "connected", "disconnected", "stale" |
| Stats Panel      | `#stats-panel`                              | Collapsible; FPS, uptime, frames, system info     |
| Tab Navigation   | `.tab-navigation` (buttons with `data-tab`) | Switch between stream and config                  |
| Config Panel     | `#config-panel`                             | Shows system configuration details                |
| Last Updated     | `.last-updated`                             | Relative timestamp display                        |

**States:**

- `.connection-status` classes: `"connecting"` (amber), `"connected"` (green), `"stale"` (amber), `"disconnected"` (red)
- `.loading-overlay` disappears when stream loads
- Controls hidden on desktop (hover-revealed), always visible on mobile
- Stats panel collapsible on mobile/tablet via `.stats-header` button

**Responsive Behavior:**

- Desktop (>1024px): Side-by-side layout (video left, stats right)
- Tablet (768-1024px): Single column, stats toggleable
- Mobile (<480px): Full width, stats collapsed by default, control text hidden (icon-only)

### Management Mode (`/` - management.html)

**Key Elements:**

| Element           | Selector                                                                                                                              | Purpose                                          |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| Header            | `.header`                                                                                                                             | Title, description                               |
| Node Form         | `#node-form`                                                                                                                          | Add/edit node; fields: ID, name, URL, auth, etc. |
| Form Feedback     | `#form-feedback`                                                                                                                      | Success/error messages                           |
| Node Table        | `#nodes-table-body`                                                                                                                   | List of registered nodes with status pills       |
| Node Status Pills | `.status-{ready\|error\|unknown}`                                                                                                     | Color-coded node health (green, red, gray)       |
| Edit Button       | `button[data-action="edit"]`                                                                                                          | Populate form for editing                        |
| Delete Button     | `button[data-action="delete"]`                                                                                                        | Remove node with confirmation                    |
| Form Inputs       | `input#node-id`, `input#node-name`, `input#base-url`, `select#transport`, `select#auth-type`, `input#bearer-token`, `textarea#labels` | Form fields                                      |
| Save Button       | `button[type="submit"]`                                                                                                               | Submit form (POST for new, PUT for edit)         |
| Cancel Button     | `.node-form-cancel` (shown during edit)                                                                                               | Reset form to "Add node" mode                    |
| Empty State       | `.empty-state-message`                                                                                                                | "No nodes registered" message                    |

**States:**

- Form shows "Add node" title when creating, "Edit node {id}" when editing
- "Save node" and "Cancel edit" buttons appear only during edit
- Status pills update every 5 seconds (`.status-ready` green, `.status-error` red, `.status-unknown` gray)
- Form feedback area shows color-coded messages (green success, red error)
- Row actions: edit, delete buttons on each row

**Responsive Behavior:**

- Desktop (>1024px): Two-column layout (form left ~320px fixed, table right)
- Tablet (768-1024px): Form above table, stacked vertically
- Mobile (<480px): Form full width, table scrollable, button labels hidden on very small screens

---

## Audit Methodology

### Phase 1: Setup & Navigation

1. **Start mock server** (if local):

   ```bash
   MOCK_CAMERA=true FLASK_ENV=development python3 pi_camera_in_docker/main.py
   ```

   Or use Docker:

   ```bash
   docker compose --profile webcam -e MOCK_CAMERA=true up
   ```

2. **Initialize Playwright browser:**

   ```javascript
   const browser = await chromium.launch();
   const context = await browser.newContext();
   const page = await context.newPage();
   ```

3. **Navigate to webcam mode:**

   ```javascript
   await page.goto("http://localhost:8000", { waitUntil: "networkidle" });
   ```

4. **Capture initial state** (screenshot at default viewport 1280×720):
   ```javascript
   await page.screenshot({ path: "webcam-initial-desktop.png" });
   ```

### Phase 2: Webcam Mode Audit

#### **Visual & Layout Inspection**

1. **Stream area:**
   - [ ] Video container visible, correct aspect ratio (4:3)
   - [ ] Stream image loads (check `img#video-stream` `src` includes `/stream.mjpg?`)
   - [ ] No layout shift when video loads
   - [ ] Loading overlay disappears after stream loads
   - [ ] No horizontal scroll/overflow

2. **Header & navigation:**
   - [ ] Header sticky at top (stays visible when scrolling)
   - [ ] Logo/title visible
   - [ ] Tab buttons (Stream/Config) clearly clickable
   - [ ] Connection status indicator visible, correct color (should be green initially)
   - [ ] No text truncation in header

3. **Controls:**
   - [ ] Refresh, fullscreen buttons present
   - [ ] Buttons have hover states (cursor changes, background darkens on desktop)
   - [ ] On mobile: buttons always visible (not hidden)
   - [ ] Touch targets minimum 44×44px on mobile
   - [ ] Button icons recognizable

4. **Stats panel:**
   - [ ] All stat items visible: FPS, frames, uptime, frame age, resolution
   - [ ] Numeric values display correctly, no "NaN" or "--" unexpectedly
   - [ ] Last-updated timestamp shows relative time (e.g., "2m ago")
   - [ ] On mobile: stats collapsed by default, toggle button visible
   - [ ] When expanded on mobile: no overlap with video

#### **UX Flow: Stream Viewing**

1. **Page load:**
   - Navigate to `/` → page loads → video element present → loading overlay visible
   - [ ] Capture screenshot before stream loads: `await page.screenshot({ path: 'webcam-loading.png' });`

2. **Stream activation:**
   - Wait for stream to load: `await page.locator('img#video-stream').screenshot();`
   - [ ] Loading overlay disappears
   - [ ] Status indicator turns green (class `"connected"`)
   - [ ] Stats panel shows FPS > 0, frames > 0
   - [ ] Capture screenshot after stream loads: `await page.screenshot({ path: 'webcam-streaming.png' });`

3. **Refresh interaction:**
   - Click refresh button: `await page.click('button[data-action="refresh"]');`
   - [ ] Button shows loading state (spinner or opacity change)
   - [ ] Stream reloads (new timestamp in src URL)
   - [ ] Status stays green
   - [ ] Store timestamp before/after: verify query param changed (`?_t=` or similar)

4. **Tab switching:**
   - Click Config tab: `await page.click('button[data-tab="config"]');`
   - [ ] Stream video still visible but stats panel hidden or swapped
   - [ ] Config panel appears with system info (resolution, limits, mode, etc.)
   - [ ] Stats polling stops (no constant updates)
   - [ ] Click back to Stream tab: stats panel returns, polling resumes
   - [ ] Capture config tab screenshot: `await page.screenshot({ path: 'webcam-config-tab.png' });`

5. **Metrics update frequency:**
   - Watch stats panel for 10 seconds: FPS, uptime, frames should change
   - [ ] FPS value updates every 1-2 seconds (not frozen)
   - [ ] Frame count increases
   - [ ] Uptime increments every 1 second
   - [ ] Last-updated timestamp updates

#### **Responsive Design: Webcam Mode**

For each viewport, take screenshots and verify:

**Tablet (768×1024):**

- [ ] Stats panel width adjusts (no longer right sidebar)
- [ ] Stats collapse toggle button visible
- [ ] Video still 4:3 aspect ratio
- [ ] Controls always visible (not hover-only)
- [ ] Text readable (no font size < 12px)
- [ ] Buttons minimum 44×44px
- [ ] No horizontal scroll
- Capture: `await page.setViewportSize({ width: 768, height: 1024 }); await page.screenshot({ path: 'webcam-tablet.png' });`

**Mobile (375×667):**

- [ ] Video full width
- [ ] Stats panel collapsed by default
- [ ] Tab labels hidden (icon-only) or small
- [ ] Buttons still clickable (no shrinking)
- [ ] No horizontal scroll
- [ ] Video doesn't overflow below controls
- [ ] Touch targets 44×44px minimum
- Capture: `await page.setViewportSize({ width: 375, height: 667 }); await page.screenshot({ path: 'webcam-mobile.png' });`

#### **Error Scenarios: Webcam Mode**

1. **Stream unavailable (503 response):**
   - Mock `/stream.mjpg` to return 503
   - [ ] Status indicator turns red or amber
   - [ ] Error message displays (if applicable)
   - [ ] Retry button visible or auto-retry happening
   - [ ] Page doesn't crash

2. **Stats fetch fails:**
   - Mock `/metrics` to return 503
   - [ ] Stats panel shows "--" or "N/A" for affected fields
   - [ ] Last-updated timestamp shows error or stale marker
   - [ ] Polling retries (exponential backoff)
   - [ ] Rest of page functional

3. **Network timeout:**
   - Slow down network (Playwright: `page.route('**/*', route => setTimeout(() => route.continue(), 5000))`)
   - [ ] Loading spinner visible during fetch
   - [ ] No UI freeze
   - [ ] Timeout error message visible after ~5-10s
   - [ ] Retry mechanism active

4. **Stale stream (frame age > MAX_FRAME_AGE_SECONDS):**
   - If frame hasn't updated in 10+ seconds
   - [ ] Status indicator shows "stale" (amber)
   - [ ] Message distinguishes "stale stream" from "disconnected"
   - [ ] Suggests refresh action

#### **Accessibility: Webcam Mode**

1. **Keyboard navigation:**
   - [ ] Tab key cycles through: tabs → buttons → any links
   - [ ] Enter/Space on buttons triggers action
   - [ ] Focus outline visible on all interactive elements
   - [ ] Focus order logical (top-to-bottom, left-to-right)

2. **ARIA & semantic HTML:**
   - [ ] `.status-indicator` has `role="status"` and `aria-live="polite"`
   - [ ] Tab buttons have `role="tab"` or semantic `<button>` tag
   - [ ] Image alt text present on video (if applicable)
   - [ ] No orphaned text (all labels associated with inputs)

3. **Color contrast:**
   - [ ] Text on backgrounds meets WCAG AA minimum (4.5:1 for body text, 3:1 for UI)
   - [ ] Status colors (green/red/amber) not sole indicator of meaning
   - [ ] Check using tool: `axe-core` or manual color contrast checker

4. **Loading states:**
   - [ ] "Loading..." text visible, not just spinner
   - [ ] Spinner has `role="status"` and `aria-label="Loading"` or similar

---

### Phase 3: Management Mode Audit

#### **Visual & Layout Inspection**

1. **Form area:**
   - [ ] Form header shows "Add node" or "Edit node {id}"
   - [ ] Form fields visible and properly labeled:
     - Node ID (text, disabled during edit)
     - Node Name (text)
     - Base URL (text, with validation feedback)
     - Transport (dropdown: "http", "docker")
     - Auth Type (dropdown: "none", "bearer")
     - Bearer Token (text, hidden if auth type is "none")
     - Capabilities (comma-separated text area)
     - Labels (JSON textarea)
   - [ ] Form feedback area clear (success/error message visible)
   - [ ] Save button labeled "Save node"
   - [ ] No form elements cut off or overlapping

2. **Table area:**
   - [ ] Table header clear (columns: Node, URL, Transport, Status, Stream, Actions)
   - [ ] Node rows display correctly:
     - [ ] Node ID and name in first column
     - [ ] URL truncated if long (no overflow)
     - [ ] Status pill color-coded (green=ready, red=error, gray=unknown)
     - [ ] Stream availability indicated (yes/no or icon)
     - [ ] Edit/Delete buttons present and clickable
   - [ ] No horizontal scroll if content fits
   - [ ] Empty state message shown when no nodes: "No nodes registered"

3. **Responsive:**
   - [ ] Desktop (>1024px): form left side (320px), table right side
   - [ ] Tablet (768-1024px): form full width, table scrollable below
   - [ ] Mobile (<480px): form full width, table scrollable with horizontal scroll for columns

#### **UX Flow: Node Management**

1. **Initial load:**
   - Navigate to `/` (management mode)
   - [ ] Page loads → existing nodes list appears (or empty state shown)
   - [ ] Status pills for each node (if any exist)
   - [ ] Capture screenshot: `await page.screenshot({ path: 'management-initial.png' });`

2. **Add node workflow:**
   - [ ] Form shows "Add node" title
   - [ ] Fill form fields:
     ```javascript
     await page.fill("input#node-id", "cam-office");
     await page.fill("input#node-name", "Office Camera");
     await page.fill("input#base-url", "http://192.168.1.101:8000");
     await page.selectOption("select#transport", "http");
     await page.selectOption("select#auth-type", "bearer");
     await page.fill("input#bearer-token", "secret-token-123");
     ```
   - Click Save: `await page.click('button[type="submit"]');`
   - [ ] Form feedback shows success message (green)
   - [ ] Form resets (fields cleared, title back to "Add node")
   - [ ] New row appears in table
   - [ ] New node has status pill (color depends on probe result)
   - [ ] Capture screenshot: `await page.screenshot({ path: 'management-node-added.png' });`

3. **Edit node workflow:**
   - Click Edit button: `await page.click('button[data-action="edit"][data-node-id="cam-office"]');`
   - [ ] Form title changes to "Edit node cam-office"
   - [ ] Form fields populate with existing node data
   - [ ] Node ID field disabled/readonly
   - [ ] "Save node" and "Cancel edit" buttons visible
   - Edit one field: `await page.fill('input#node-name', 'Office Camera - Updated');`
   - Click Save: `await page.click('button[type="submit"]');`
   - [ ] Form feedback shows success
   - [ ] Table row updates with new name
   - [ ] Form resets to "Add node" mode
   - [ ] Capture screenshot: `await page.screenshot({ path: 'management-node-edited.png' });`

4. **Delete node workflow:**
   - Click Delete button: `await page.click('button[data-action="delete"][data-node-id="cam-office"]');`
   - [ ] Confirmation prompt appears (browser native or custom)
   - [ ] User cancels → node remains
   - Click Delete again, confirm: `await page.click('button[data-action="delete"][data-node-id="cam-office"]'); await page.click('button:has-text("Confirm")');` (or browser confirm)
   - [ ] Node row disappears from table
   - [ ] If last node, empty state message shows
   - [ ] Capture screenshot: `await page.screenshot({ path: 'management-node-deleted.png' });`

5. **Status polling:**
   - Wait 5 seconds, observe status pills
   - [ ] Status pills update (colors may change based on probe results)
   - [ ] No errors in console (`await page.on('console', msg => console.log(msg));`)
   - [ ] No excessive requests (should poll every 5s per node, not more frequently)

#### **Responsive Design: Management Mode**

**Tablet (768×1024):**

- [ ] Form full width
- [ ] Table below form, columns adjusted
- [ ] No horizontal scroll if columns fit
- [ ] Button labels visible or icons clear
- Capture: `await page.setViewportSize({ width: 768, height: 1024 }); await page.screenshot({ path: 'management-tablet.png' });`

**Mobile (375×667):**

- [ ] Form full width, fields stacked vertically
- [ ] Table below, with horizontal scroll for columns
- [ ] Touch targets 44×44px minimum
- [ ] Button labels abbreviated or icon-only
- [ ] No layout breaks
- Capture: `await page.setViewportSize({ width: 375, height: 667 }); await page.screenshot({ path: 'management-mobile.png' });`

#### **Error Scenarios: Management Mode**

1. **Form validation errors:**
   - Submit empty form: `await page.click('button[type="submit"]');`
   - [ ] Error messages appear below required fields (red text)
   - [ ] "Node ID required", "Name required", etc.
   - [ ] Form not submitted

2. **Invalid URL format:**
   - Enter invalid URL: `await page.fill('input#base-url', 'not-a-url');`
   - Click Save: `await page.click('button[type="submit"]');`
   - [ ] Error message shows (e.g., "Invalid URL format")
   - [ ] Form remains open with field highlighted

3. **Node unreachable (status probe fails):**
   - Add node with unreachable URL: `base_url: "http://192.168.1.999:8000"`
   - [ ] Node added to table
   - [ ] Status pill shows red/error (within 5 seconds)
   - [ ] No page crash, error handled gracefully

4. **JSON labels invalid:**
   - Enter invalid JSON in labels field: `{"key": "value", invalid}`
   - Click Save: `await page.click('button[type="submit"]');`
   - [ ] Error feedback shown (e.g., "Invalid JSON in labels")
   - [ ] Form not submitted

#### **Accessibility: Management Mode**

1. **Keyboard navigation:**
   - [ ] Tab cycles through form fields → buttons → table rows
   - [ ] Enter/Space on buttons triggers action
   - [ ] Table rows accessible via keyboard (arrow keys to navigate rows)
   - [ ] Focus outline always visible

2. **Form labels:**
   - [ ] Every input has associated `<label>` or aria-label
   - [ ] Labels readable (no tiny font)
   - [ ] Required fields marked with `*` or aria-required

3. **Color contrast:**
   - [ ] Status pills readable (green, red, gray on dark background)
   - [ ] Table text contrast meets WCAG AA (4.5:1 for body)
   - [ ] Form input text visible

4. **Screen reader support:**
   - [ ] Table has `role="table"` or semantic structure
   - [ ] Status updates announced (aria-live region)
   - [ ] Error messages associated with form fields
   - [ ] Button purposes clear (e.g., "Edit node X", "Delete node Y")

---

## Debugging Helpers

### Page State Snapshot

```javascript
async function capturePageState(page, filename) {
  // Screenshot
  await page.screenshot({ path: filename });

  // DOM state
  const domState = await page.evaluate(() => {
    return {
      title: document.title,
      url: window.location.href,
      viewportSize: { width: window.innerWidth, height: window.innerHeight },
      visibleElements: {
        header: document.querySelector(".header")?.offsetHeight,
        video: document.querySelector(".video-container")?.offsetHeight,
        stats: document.querySelector("#stats-panel")?.offsetHeight,
        form: document.querySelector("#node-form")?.offsetHeight,
        table: document.querySelector("#nodes-table-body")?.offsetHeight,
      },
      hasErrors: document.querySelectorAll('.error, [role="alert"]').length > 0,
    };
  });

  console.log(`State (${filename}):`, domState);
  return domState;
}

// Usage:
await capturePageState(page, "webcam-state.png");
```

### Responsive Test Loop

```javascript
async function testResponsive(page, baseUrl, filename) {
  const viewports = [
    { name: "desktop", width: 1280, height: 720 },
    { name: "tablet", width: 768, height: 1024 },
    { name: "mobile", width: 375, height: 667 },
  ];

  for (const vp of viewports) {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    await page.screenshot({ path: `${filename}-${vp.name}.png` });
    console.log(`✓ Tested ${vp.name} (${vp.width}×${vp.height})`);
  }
}

// Usage:
await testResponsive(page, "http://localhost:8000", "webcam");
```

### Interaction Trace

```javascript
async function traceInteraction(page, actionName, interactionFn) {
  console.log(`[START] ${actionName}`);
  const startTime = Date.now();

  try {
    await interactionFn();
    const elapsed = Date.now() - startTime;
    console.log(`[SUCCESS] ${actionName} (${elapsed}ms)`);
    return { success: true, elapsed };
  } catch (error) {
    console.log(`[ERROR] ${actionName}:`, error.message);
    return { success: false, error: error.message };
  }
}

// Usage:
await traceInteraction(page, "Add Node", async () => {
  await page.fill("input#node-id", "test-cam");
  await page.click('button[type="submit"]');
  await page.waitForSelector(".success-message");
});
```

---

## Output Format

### Audit Report Structure

**File:** `UI-AUDIT-REPORT.md`

```markdown
# Motion-in-Ocean UI Audit Report

**Date:** 2026-02-08  
**Auditor:** AI Agent  
**Scope:** Webcam + Management modes, responsive (desktop/tablet/mobile)  
**Duration:** 30 minutes

## Summary

- **Overall Assessment:** [PASS / PASS_WITH_FINDINGS / FAIL]
- **Blockers Found:** [Number]
- **Design Issues:** [Number]
- **Accessibility Issues:** [Number]
- **Responsive Design Issues:** [Number]

## Detailed Findings

### Category: Layout & Visual Design

#### Finding 1: [Title]

- **Severity:** [Critical / Major / Minor]
- **Mode:** Webcam / Management / Both
- **Location:** [Selector or description]
- **Description:** [What's wrong]
- **Evidence:** [Screenshot path]
- **Recommendation:** [How to fix]

### Category: Responsive Design

#### Finding 2: [Title]

- **Severity:** [Critical / Major / Minor]
- **Viewport:** 375×667 (mobile)
- **Description:** [Layout issue at mobile size]
- **Evidence:** [Screenshot path]

### Category: Accessibility

#### Finding 3: [Title]

- **Severity:** [Critical / Major / Minor]
- **Issue:** [WCAG violation]
- **Affected Users:** [Screen reader users, keyboard-only, etc.]
- **Recommendation:** [Fix required]

### Category: UX Flows

#### Finding 4: [Title]

- **Flow:** Stream Viewing / Node Management
- **Issue:** [User friction, unclear feedback, etc.]
- **Evidence:** [Screenshots or interaction trace]

### Category: Error Handling

#### Finding 5: [Title]

- **Scenario:** [Error condition, e.g., network timeout]
- **Current Behavior:** [What happens]
- **Expected Behavior:** [What should happen]
- **Evidence:** [Screenshot path]

## Pass Checklist

- [x] Header sticky and visible at all breakpoints
- [x] Video stream loads and plays within 3 seconds
- [x] Controls accessible on mobile (44×44px minimum)
- [x] Tab navigation works at all breakpoints
- [x] Node form submits without XSS issues
- [x] Error messages clearly displayed
- [x] Keyboard navigation functional
- [x] Focus outline visible

## Screenshots

- `webcam-initial-desktop.png` — Initial state at 1280×720
- `webcam-tablet.png` — Responsive test at 768×1024
- `webcam-mobile.png` — Responsive test at 375×667
- `management-initial.png` — Initial state at 1280×720
- `management-tablet.png` — Responsive test at 768×1024
- `management-mobile.png` — Responsive test at 375×667

## Next Steps

1. [Fix critical finding X]
2. [Design review for finding Y]
3. [Accessibility audit with WCAG validator]
4. [Retest after fixes]
```

---

## Integration & Execution

### Local Audit (Manual)

1. **Start server:**

   ```bash
   MOCK_CAMERA=true python3 pi_camera_in_docker/main.py
   # or
   docker compose --profile webcam -e MOCK_CAMERA=true up
   ```

2. **Run Playwright inspector:**

   ```bash
   npx playwright install  # if needed
   npx playwright codegen http://localhost:8000  # interactive record
   ```

3. **Execute audit script:**

   ```javascript
   // audit.js (template in this skill)
   const { chromium } = require("@playwright/test");

   (async () => {
     const browser = await chromium.launch();
     const page = await browser.newPage();

     // Webcam mode
     await page.goto("http://localhost:8000");
     // ... audit steps ...

     // Management mode (requires server running in management mode)
     await page.goto("http://localhost:8001/");
     // ... audit steps ...

     await browser.close();
   })();
   ```

   Run: `node audit.js`

4. **Capture artifacts:**
   - Screenshots saved to `./audit-results/`
   - Generate report: `UI-AUDIT-REPORT.md`
   - Commit findings to PR

### CI/CD Integration (Optional)

If using GitHub Actions for automated screenshot repo:

```yaml
name: UI Audit

on: [pull_request]

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: "18"
      - run: npm install
      - run: docker compose --profile webcam -e MOCK_CAMERA=true up -d
      - run: npx playwright install
      - run: node audit-script.js
      - uses: actions/upload-artifact@v3
        with:
          name: audit-screenshots
          path: audit-results/
```

---

## Failure / Stop Conditions

1. **Stop if server unreachable:** Cannot connect to `http://localhost:8000` (or configured URL).
   - **Resolution:** Verify Flask/Docker server running, port correct, firewall not blocking.

2. **Stop if UI structure differs significantly from selectors in this skill:**
   - Example: `.video-container` doesn't exist, form fields renamed
   - **Resolution:** Update selectors based on actual HTML; compare with [PRD-frontend.md](../../PRD-frontend.md).

3. **Stop if mock camera mode unavailable:**
   - Cannot test without camera hardware or mock mode disabled
   - **Resolution:** Verify `MOCK_CAMERA=true` environment variable set or hardware available.

4. **Stop if browser automation blocked:**
   - Playwright blocked by CSP or server-side restrictions
   - **Resolution:** Check server security headers, disable CSP for test environment if necessary.

5. **Stop if findings too vague to act upon:**
   - Example: "Layout looks off" without specific dimensions/selectors
   - **Resolution:** Take screenshot, measure exact pixels, describe specific issue and viewport.

---

## Related Documentation

- [PRD-frontend.md](../../PRD-frontend.md) — UI/UX requirements, feature specification
- [PRD-backend.md](../../PRD-backend.md) — Backend API endpoints used by UI
- [CONTRIBUTING.md](../../CONTRIBUTING.md) — Development guidelines
- [README.md architectural concepts](../../README.md#architecture--key-concepts) — System overview

---

## Tools & Resources

- **Playwright Documentation:** [playwright.dev](https://playwright.dev)
- **Playwright Inspector:** `npx playwright codegen` (interactive UI recording)
- **Chromium DevTools:** Built into Playwright, accessible via `page.pause()` or `page.close()` with visual inspection
- **Color Contrast Checker:** [WebAIM Contrast](https://webaim.org/resources/contrastchecker/)
- **WCAG 2.1 Guidelines:** [w3.org/WAI/WCAG21/quickref/](https://www.w3.org/WAI/WCAG21/quickref/)
- **Axe Accessibility Tool:** `npm install @axe-core/playwright` (programmatic accessibility checks)
