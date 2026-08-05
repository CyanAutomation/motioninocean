---
name: ui-playwright
description: Audit motion-in-ocean web UI (streaming viewer & node management) using Playwright; inspect layout, UX flows, accessibility, responsive design, and error handling.
owner: motion-in-ocean team
last-reviewed: 2026-08-05
category: Design
compatible-repo-areas:
  - pi_camera_in_docker/templates/
  - pi_camera_in_docker/static/
  - tests/ui/
  - playwright.ui.config.mjs
  - Makefile
---

## Purpose

Enable developers to systematically inspect and evaluate the motion-in-ocean web UI across both application modes (webcam streaming viewer and management node interface) using Playwright browser automation. This skill provides structured audit methodology to capture UI state, validate workflows, inspect responsive design, check accessibility compliance, and identify UX/design issues. This is **exploratory auditing** (evaluation/inspection) rather than automated testing (verification/regression).

## Scope and trigger conditions

Apply this skill when:

- Performing design QA before PR merge (UI changes, component updates, visual regressions)
- Validating responsive layout across device sizes (mobile, tablet, desktop)
- Checking accessibility compliance (ARIA labels, keyboard navigation, color contrast)
- Exploring error scenarios and edge cases (stream failures, network timeouts, validation errors)
- Auditing UX flows end-to-end (stream viewing, node management, tab switching, form submission)
- Evaluating consistency of design tokens (colors, spacing, typography, button states)
- Documenting UI behavior changes for release notes or design updates
- Testing both webcam mode (streaming viewer) and management mode (node registry) in same session

Do NOT use this skill for:

- Writing automated regression tests (use [`frontend-testing-linting`](../frontend-testing-linting/SKILL.md) instead)
- Validating API correctness (use [`ci-triage`](../ci-triage/SKILL.md) instead)
- Performance benchmarking or load testing
- Local component-level testing without running full application

## Required inputs

- Running motion-in-ocean instance (local mock via Flask or Docker Compose)
- Playwright browser automation framework installed (`npm install @playwright/test`)
- Access to UI specifications ([PRD-frontend.md](../../PRD-frontend.md), design mockups)
- Knowledge of accessibility standards (WCAG 2.1 Level AA)
- Ability to modify environment (set `MOCK_CAMERA=true`, change ports, etc.)
- Optional: Accessibility testing tools (axe-core, manual color contrast checker)

## Step-by-step workflow

### Phase 1: Setup & Launch

**Start mock application (if local development):**

```bash
# Option 1: Flask development server
MOCK_CAMERA=true FLASK_ENV=development python3 pi_camera_in_docker/main.py

# Option 2: Docker Compose
docker compose --profile webcam -f docker-compose.yml -f docker-compose.mock.yml up
```

**Initialize Playwright:**

```javascript
const { chromium } = require('playwright');

async function auditUI() {
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();
  
  // Set default viewport
  await page.setViewportSize({ width: 1280, height: 720 });
  
  // Enable console message capture
  page.on('console', msg => console.log(`[${msg.type()}] ${msg.text()}`));
  
  // Proceed with audit...
}
```

### Phase 2: Webcam Mode Audit (Streaming Viewer)

#### Visual & Layout Inspection

1. **Navigate to webcam mode:**
   ```javascript
   await page.goto("http://localhost:8000", { waitUntil: "networkidle" });
   ```

2. **Verify key elements visible:**
   - Header (sticky, contains logo/title, tabs, status indicator)
   - Video container (4:3 aspect ratio)
   - Video stream (`img#video-stream`)
   - Loading overlay (visible during load, disappears after stream loads)
   - Video controls (refresh, fullscreen buttons)
   - Status indicator (colored pill: green/red/amber)
   - Stats panel (FPS, frames, uptime, frame age)
   - Tab navigation (Stream/Config tabs)

3. **Verify initial state:**
   - No layout shift when video loads
   - No horizontal scroll/overflow
   - All text readable (min 12px font)
   - Buttons minimum 44×44px touch targets

#### Stream Viewing Workflow

1. **Stream load:**
   - Page loads → loading overlay visible
   - Capture: `await page.screenshot({ path: 'webcam-loading.png' });`
   - Wait for stream: `await page.locator('img#video-stream').waitFor({ timeout: 10000 });`
   - Loading overlay disappears
   - Status indicator turns green

2. **Stats panel updates:**
   - Watch stats for 10 seconds
   - Verify FPS updates every 1-2 seconds
   - Verify frame count increases
   - Verify uptime increments every 1 second
   - Verify last-updated timestamp refreshes
   - Capture: `await page.screenshot({ path: 'webcam-streaming.png' });`

3. **Refresh interaction:**
   ```javascript
   await page.click('button[data-action="refresh"]');
   ```
   - Button shows loading state
   - Stream reloads (new timestamp in src URL)
   - Status stays green

4. **Tab switching:**
   ```javascript
   await page.click('button[data-tab="config"]');
   ```
   - Config panel appears with system information
   - Stats polling stops
   - Click back to Stream: stats panel returns, polling resumes

#### Responsive Design Testing

Test at three viewports with screenshots:

**Desktop (1280×720):**
```javascript
await page.setViewportSize({ width: 1280, height: 720 });
await page.screenshot({ path: 'webcam-desktop.png' });
```

**Tablet (768×1024):**
```javascript
await page.setViewportSize({ width: 768, height: 1024 });
await page.screenshot({ path: 'webcam-tablet.png' });
```

**Mobile (375×667):**
```javascript
await page.setViewportSize({ width: 375, height: 667 });
await page.screenshot({ path: 'webcam-mobile.png' });
```

**Verification:**
- Desktop: Side-by-side layout (video left, stats right)
- Tablet: Single column, stats toggleable
- Mobile: Full width, stats collapsed, buttons still clickable (44×44px)

#### Error Scenarios

1. **Stream unavailable (mock 503):**
   - Status indicator turns red
   - Error message or retry indication visible
   - Page doesn't crash

2. **Stats fetch fails:**
   - Stats panel shows "--" or "N/A"
   - Rest of page functional
   - Polling retries after timeout

3. **Stale stream:**
   - Status shows "stale" (amber) after 10+ seconds without frame update
   - Message distinguishes stale from disconnected

#### Accessibility

1. **Keyboard navigation:**
   ```javascript
   // Tab through interactive elements
   await page.press('body', 'Tab'); // Focus 1st interactive element
   await page.press('body', 'Tab'); // Focus 2nd, etc.
   ```
   - Focus outline visible on all elements
   - Enter/Space triggers button actions
   - Focus order is logical (top-to-bottom, left-to-right)

2. **Semantic HTML & ARIA:**
   - Status indicator: `role="status"` and `aria-live="polite"`
   - Tab buttons: semantic `<button>` tags or `role="tab"`
   - Images: alt text present

3. **Color contrast:**
   - Text/background contrast ≥ 4.5:1 (body text, WCAG AA)
   - UI elements ≥ 3:1 (WCAG AA)
   - Status colors not sole indicator of meaning

### Phase 3: Management Mode Audit (Node Registry)

#### Visual & Layout Inspection

1. **Navigate to management mode:**
   ```javascript
   await page.goto("http://localhost:8001", { waitUntil: "networkidle" });
   ```

2. **Verify form and table:**
   - Form header: "Add node" or "Edit node {id}"
   - Form fields: ID, name, URL, transport, auth type, bearer token, labels
   - Form feedback area (success/error messages)
   - Save button labeled appropriately
   - Table with headers: Node, URL, Transport, Status, Stream, Actions
   - Each row has node info + status pill + edit/delete buttons

#### Node Management Workflow

1. **Add node:**
   ```javascript
   await page.fill("input#node-id", "cam-office");
   await page.fill("input#node-name", "Office Camera");
   await page.fill("input#base-url", "http://192.168.1.101:8000");
   await page.selectOption("select#transport", "http");
   await page.selectOption("select#auth-type", "bearer");
   await page.fill("input#bearer-token", "secret-token");
   await page.click('button[type="submit"]');
   ```
   - Form feedback shows success (green)
   - Form resets
   - New row appears in table
   - Status pill present (color depends on probe result)

2. **Edit node:**
   ```javascript
   await page.click('button[data-action="edit"][data-node-id="cam-office"]');
   ```
   - Form title changes to "Edit node cam-office"
   - Fields populate with existing data
   - Node ID field is disabled
   - Modify and save
   - Table row updates, form resets

3. **Delete node:**
   ```javascript
   await page.click('button[data-action="delete"][data-node-id="cam-office"]');
   // Confirm in dialog
   ```
   - Node row disappears
   - Empty state shows if no nodes remain

4. **Status polling:**
   - Wait 5 seconds
   - Status pills update (colors may change)
   - No console errors
   - Poll frequency ≈ 5s per node

#### Responsive Design

**Tablet (768×1024):**
```javascript
await page.setViewportSize({ width: 768, height: 1024 });
```
- Form full width, table below
- Columns adjusted for narrow viewport

**Mobile (375×667):**
```javascript
await page.setViewportSize({ width: 375, height: 667 });
```
- Form full width, stacked fields
- Table with horizontal scroll
- Touch targets 44×44px

#### Error Scenarios

1. **Form validation:**
   - Submit empty form → errors on required fields
   - Invalid URL → error message shown
   - Invalid JSON in labels → error feedback

2. **Unreachable node:**
   - Add node with unreachable URL
   - Status pill shows red/error after 5 seconds
   - Page doesn't crash

### Phase 4: Cross-Mode Validation

- Both modes work in same browser session
- No state leakage between modes
- Navigation between modes clean (no leftover UI elements)

## Validation checklist

**Webcam Mode:**
- [ ] Stream loads within 3 seconds
- [ ] Status indicator is green when streaming
- [ ] Stats panel updates every 1-2 seconds
- [ ] Refresh button reloads stream
- [ ] Tab switching works smoothly
- [ ] Responsive layout correct at desktop/tablet/mobile
- [ ] No layout shift, no horizontal scroll
- [ ] Keyboard navigation works (Tab, Enter, Space)
- [ ] Color contrast meets WCAG AA
- [ ] Error states handled gracefully (503, timeout, stale)

**Management Mode:**
- [ ] Form submits new nodes successfully
- [ ] Form feedback messages clear (green success, red error)
- [ ] Table displays nodes with status pills
- [ ] Edit/delete workflows complete without errors
- [ ] Status pills update every 5 seconds
- [ ] Form validation prevents invalid submissions
- [ ] Responsive layout correct at desktop/tablet/mobile
- [ ] Keyboard navigation works on all inputs/buttons
- [ ] No console errors during operations

**Accessibility (Both Modes):**
- [ ] All buttons/links have visible focus outline
- [ ] Tab key navigates all interactive elements
- [ ] Enter/Space trigger button actions
- [ ] ARIA labels present where needed
- [ ] Color contrast ≥ 4.5:1 for body text
- [ ] Touch targets ≥ 44×44px on mobile
- [ ] Error messages associated with form fields

## Source of truth

- [pi_camera_in_docker/templates/index.html](../../pi_camera_in_docker/templates/index.html) — Webcam mode HTML
- [pi_camera_in_docker/templates/management.html](../../pi_camera_in_docker/templates/management.html) — Management mode HTML
- [pi_camera_in_docker/static/js/app.js](../../pi_camera_in_docker/static/js/app.js) — Webcam mode logic
- [pi_camera_in_docker/static/js/management.js](../../pi_camera_in_docker/static/js/management.js) — Management mode logic
- [pi_camera_in_docker/static/css/](../../pi_camera_in_docker/static/css/) — Styles and breakpoints
- [PRD-frontend.md](../../PRD-frontend.md) — Feature requirements and design spec
- [tests/ui/](../../tests/ui/) — Reference UI test patterns
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/) — Accessibility standards

## Common failure modes and recovery actions

| Failure | Cause | Recovery |
| --- | --- | --- |
| Stream doesn't load | Mock camera disabled or /stream endpoint broken | Enable mock: `MOCK_CAMERA=true`; check Flask logs for endpoint errors |
| Stats panel frozen | Stats polling stopped or API error | Check `/metrics` endpoint in browser; verify CORS if different port |
| Form submission fails silently | Validation error not shown or API error not caught | Check browser console for errors; verify `/api/nodes` endpoint exists |
| Status pills never update | Status polling disabled or unreachable nodes | Check browser console; verify management mode is running on :8001 |
| Layout broken on mobile | CSS media queries not applied or viewport meta tag missing | Verify viewport meta tag; check CSS breakpoints in `style.css` |
| Keyboard navigation skips elements | Tab index incorrect or interactive elements not semantic | Use browser DevTools; verify all buttons are `<button>` not `<div onclick>` |
| Color contrast fails WCAG | Foreground/background colors too similar | Use contrast checker tool; increase font weight or darken background |
| Modal/dialog not dismissable | Keyboard handler missing or focus trap broken | Check handler on Escape key; verify modal catches blur outside |
| Performance degrades after many operations | Memory leak or event listeners not cleaned up | Check browser DevTools Memory profiler; verify listeners are removed on unmount |
| Error messages not visible | Display none or font color white on white | Check browser DevTools; verify error message styling |

## Maintenance notes

- Review this skill quarterly; especially when templates, styles, or JavaScript changes
- Update UI element selectors if HTML structure changes
- Verify accessibility standards compliance annually (WCAG versions evolve)
- Test on actual target devices (Raspberry Pi browser, mobile browsers) quarterly
- Ensure mock camera mode is tested alongside real camera mode
- Document any new UI features or workflows that need audit coverage
- Update audit methodology if new UI modes or components added

---

## Related Skills

- **After auditing issues:** [`front-end-design`](../front-end-design/SKILL.md) — Design principles for fixing UI issues
- **Implementation of changes:** [`contributor-workflow`](../contributor-workflow/SKILL.md) — Contributor workflow for PR submission
- **Validation before merge:** [`ci-quality-gates`](../ci-quality-gates/SKILL.md) — Ensure all checks pass before merge
- **Design specifications:** [`mermaid-creator`](../mermaid-creator/SKILL.md) — Create diagrams showing UI flows
- **If bugs found:** [`ci-triage`](../ci-triage/SKILL.md) — Triage failed tests or CI issues
- **Feature flag testing:** [`feature-flag-management`](../feature-flag-management/SKILL.md) — Test UI behind feature flags (mock camera, new components)
