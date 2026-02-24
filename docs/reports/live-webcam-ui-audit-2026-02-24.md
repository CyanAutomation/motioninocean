# Live Webcam UI Audit (Playwright CLI)

- Date: 2026-02-24
- Target: `https://motioninocean-482194634678.europe-west1.run.app`
- Tooling: `playwright-cli` (Chromium, headless)
- Viewports tested: `1280x720`, `768x1024`, `375x667`

## Findings

### 1) Critical: Mobile/Tablet layout overlap from dual fixed navigation rails

- Severity: **Critical**
- Affected viewports: `768x1024`, `375x667`
- Impact:
  - Left fixed rail overlays main content, clipping headings/text and reducing usable width.
  - Bottom fixed rail is also present simultaneously, creating stacked navigation chrome and further reducing usable content area.
  - Primary content is partially obscured and harder to read/interact with.
- Evidence:
  - Screenshots:
    - `screenshots/live2-tablet-stream.png`
    - `screenshots/live2-mobile-stream.png`
    - `screenshots/live2-mobile-settings.png`
  - DOM metrics at `375x667`:
    - Left rail fixed rect: `x=0`, `width=82`, `height=667`
    - Bottom rail fixed rect: `y=610`, `height=57`
    - Main content starts at `left=8` (underlaps left rail region)
    - Fixed elements include both:
      - `nav.tab-navigation.webcam-side-rail`
      - `nav.tab-navigation.webcam-bottom-rail`
- Repro steps:
  1. Open app.
  2. Resize to tablet (`768x1024`) or mobile (`375x667`).
  3. Observe content clipping under the left rail while bottom rail remains visible.

### 2) Info: Browser console verbose warning about password input outside form

- Severity: **Info**
- Impact: Not a blocking UI defect, but indicates markup inconsistency and potential accessibility/form semantics issue.
- Evidence:
  - Console log (`.playwright-cli/console-2026-02-24T22-47-58-855Z.log`):
    - `Password field is not contained in a form` (reported twice)

## No major desktop layout regressions observed

- Desktop (`1280x720`) appeared visually stable in Stream, Config, and Settings views.
- Evidence:
  - `screenshots/live2-desktop-stream.png`
  - `screenshots/live2-desktop-config.png`
  - `screenshots/live2-desktop-settings.png`
