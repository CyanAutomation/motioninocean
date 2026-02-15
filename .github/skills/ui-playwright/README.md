# UI Auditing Skill with Playwright

This directory contains comprehensive UI auditing guidance for AI agents to inspect, evaluate, and validate the motion-in-ocean web interface across both application modes (webcam streaming viewer and management node registry).

## Files

- **SKILL.md** — Complete UI auditing methodology, selectors, responsive design patterns, accessibility checks, error scenarios, debugging helpers, and output format guidance.
- **../../../audit-template.js** — Executable template script that demonstrates automated UI audit patterns. Use this as a reference or starting point for AI agents.

## Quick Start for AI Agents

### 1. Read the Skill

Start by reading [SKILL.md](SKILL.md) to understand:

- Audit methodology and mandatory rules
- Page object selectors for both UI modes
- Responsive design breakpoints (desktop/tablet/mobile)
- UX flow patterns to test
- Accessibility inspection guidelines
- Error scenario exploration

### 2. Run a Manual Audit

Inspect the UI interactively using Playwright:

```bash
# Start the server in mock mode
docker compose --profile webcam -e MOCK_CAMERA=true up -d

# Open interactive Playwright inspector
make audit-ui-interactive
# or
npx playwright codegen http://localhost:8000

# Navigate, interact, and record UI flows
```

### 3. Run an Automated Audit

Execute the template audit script:

```bash
# Full audit (both webcam and management modes)
make audit-ui

# Or choose a specific mode
make audit-ui-webcam
make audit-ui-management
```

Results are saved to `audit-results/`:

- Screenshots at each viewport (desktop/tablet/mobile)
- `UI-AUDIT-REPORT.md` with findings

### 4. Generate Findings

Create a structured audit report documenting:

- Layout and visual design issues
- Responsive design problems (specific viewport)
- Accessibility violations
- UX flow friction
- Error handling gaps
- Severity and recommendations

See SKILL.md "Output Format" section for report structure.

## Integration with Development

### Before Merging UI Changes

Request an AI agent UI audit to validate:

- Responsive design at all breakpoints
- Accessibility compliance (keyboard, ARIA, color contrast)
- User workflows end-to-end
- Error scenarios handled gracefully

### PR Review Checklist

- [ ] Layout and visual design consistent
- [ ] Responsive design validated at 3+ breakpoints
- [ ] Accessibility: keyboard navigation, ARIA labels, focus states
- [ ] Error messages clear and actionable
- [ ] No console errors during typical workflows
- [ ] Touch targets 44×44px minimum on mobile

## Documentation

- **Skill Location:** `.github/skills/ui-playwright/SKILL.md`
- **Contribution Reference:** See [CONTRIBUTING.md](../../../CONTRIBUTING.md) "UI auditing guidelines"
- **Frontend PRD:** See [PRD-frontend.md](../../../PRD-frontend.md) for UI/UX requirements
- **Backend API:** See [PRD-backend.md](../../../PRD-backend.md) for API endpoints used by UI

## Resources

- **Playwright Documentation:** <https://playwright.dev>
- **Playwright Inspector:** `npx playwright inspect` (debug specific pages)
- **Accessibility (WCAG 2.1):** <https://www.w3.org/WAI/WCAG21/quickref/>
- **WebAIM Color Contrast:** <https://webaim.org/resources/contrastchecker/>

## Common Audit Patterns

### Responsive Testing

Test at three viewports defined in SKILL.md:

- **Desktop:** 1280×720 (> 1024px)
- **Tablet:** 768×1024 (768-1024px)
- **Mobile:** 375×667 (< 480px)

Compare layout at each to verify:

- Proper element stacking/reflow
- Touch targets remain 44×44px minimum
- Text readable (no truncation)
- No horizontal scroll

### Accessibility Audit

Check programmatically:

- [ ] Keyboard tab order (Tab key cycles through interactive elements)
- [ ] ARIA labels and roles present
- [ ] Color contrast 4.5:1 (body text), 3:1 (UI components)
- [ ] Focus states visible
- [ ] Form labels associated with inputs
- [ ] Status updates announced (aria-live regions)

### Error Scenario Testing

Systematically explore failures:

- [ ] Stream unavailable (503) → graceful error display
- [ ] Network timeout → backoff and retry
- [ ] Stale stream (frame age exceeded) → status change
- [ ] Form validation → errors shown inline
- [ ] Missing data → empty state message
- [ ] Network slow → loading spinner visible

## Troubleshooting

**Q: Playwright inspector won't open**

- Ensure Node.js/npm installed: `node --version`
- Install Playwright: `npm install`
- Check port 8000 not blocked

**Q: Can't connect to server**

- Verify motion-in-ocean running: `docker ps` or `lsof -i :8000`
- Check baseUrl in audit script (default: <http://localhost:8000>)
- Ensure mock camera mode if no hardware: `MOCK_CAMERA=true`

**Q: Screenshots not captured**

- Check `audit-results/` directory writeable
- Verify Playwright browser launched successfully
- Check console output for errors

**Q: Audit findings unclear or not specific enough**

- Always include screenshot evidence
- Measure exact dimensions (pixels, breakpoint)
- Reference selector or element description
- Distinguish "cosmetic" from "blocking" issues

---

For detailed guidance, see [SKILL.md](SKILL.md).
