---
name: front-end-design
description: Use when the task asks for a visually strong landing page, website, app, prototype, demo, or game UI. This skill enforces restrained composition, image-led hierarchy, cohesive content structure, and tasteful motion while avoiding generic cards, weak branding, and UI clutter.
owner: motion-in-ocean team
last-reviewed: 2026-08-05
category: Design
compatible-repo-areas:
  - pi_camera_in_docker/static/
  - pi_camera_in_docker/templates/
  - design/
---

## Purpose

Enable designers and developers to create visually premium, restrained interfaces that prioritize clarity and hierarchy over component count. This skill enforces deliberate composition, strong imagery, sparse copy, tasteful motion, and ruthless removal of unnecessary UI elements. The goal is award-level interfaces that feel intentional and current.

## Scope and trigger conditions

Apply this skill when:

- Designing a landing page, marketing website, product homepage, or high-stakes UI
- Creating a streaming viewer, dashboard, or operational interface for motion-in-ocean
- Building a prototype, demo, or design proposal that must feel premium and cohesive
- Making decisions about imagery, typography, color, spacing, or motion
- Evaluating or critiquing existing interfaces for design quality

Do NOT use this skill for:

- Quick utility components without design intent
- Back-of-house admin tools where utility is the only goal
- Refactoring existing component libraries (unless redesigning their public face)
- Rapid prototyping where visual polish is deferred

## Required inputs

- Clear understanding of the interface goal (explain, convert, control, monitor)
- Target audience and device types (desktop, mobile, tablet)
- Brand guidelines, if applicable (colors, typography, logo)
- Content that will populate the interface (headlines, images, CTAs)
- Motion/animation framework availability (Framer Motion, CSS, native browser)
- Constraints (performance budget, accessibility requirements, responsive breakpoints)

## Step-by-step workflow

### Pre-design: Write your thesis

Before building, articulate three things in 1-2 sentences each:

1. **Visual thesis:** One sentence describing mood, material, and energy (e.g., "minimal, urgent, technical")
2. **Content plan:** Hero, support, detail, final CTA (e.g., "product shot → feature proof → workflow depth → sign-up")
3. **Interaction thesis:** 2-3 motion ideas that change the feel (e.g., "entrance sequence in hero, scroll-linked depth, hover sharpens affordance")

Each section should get one job, one dominant visual idea, and one primary takeaway or action.

### Design Principles: Beautiful Defaults

- **Start with composition, not components.** Prefer full-bleed hero or full-canvas visual anchor over modular cards.
- **Hierarchy through scale, not chrome.** Make brand/product name the loudest text; keep copy scannable within seconds.
- **Whitespace first.** Use whitespace, alignment, scale, cropping, and contrast before adding borders or shadows.
- **Limit the system:** Two typefaces maximum, one accent color by default.
- **Cardless by default.** Use sections, columns, dividers, lists, and media blocks instead of cards. Only use cards when the card is the interactive unit.
- **Treat first viewport as a poster.** Don't make it look like a document.

### Landing Pages: Default Sequence

1. **Hero:** Brand/product name, promise, CTA, one dominant visual (full-bleed image or visual plane)
2. **Support:** One concrete feature, offer, or proof point
3. **Detail:** Atmosphere, workflow, product depth, or story
4. **Final CTA:** Convert, start, visit, or contact

**Hero Rules:**
- One composition only; no hero cards or stacked elements by default
- Full-bleed image with constrained text column anchored to calm area
- Brand first, headline second, body third, CTA fourth
- Headlines 2-3 lines on desktop, readable in one glance on mobile
- All text over imagery must maintain strong contrast and clear tap targets
- Viewport budget: if header is sticky, it counts against hero height; use `calc(100svh - header-height)` or overlay
- **Acid test:** If page works without the image, the image is too weak. If brand disappears with nav hidden, hierarchy is too weak.

### App UI: Linear-Style Restraint

For dashboards, streams, node management, or operational interfaces:

- Calm surface hierarchy with strong typography and spacing
- Few colors; one accent for action/state
- Dense but readable information; minimal chrome
- Organize around: primary workspace, navigation, secondary context/inspector

**Avoid in app UI:**
- Dashboard-card mosaics
- Thick borders on every region
- Decorative gradients behind product UI
- Multiple competing accent colors
- Ornamental icons that don't improve scanning
- Panels that could be plain layout—remove unnecessary card treatment

### Imagery: Narrative Work

Imagery must earn its place:

- Use at least one strong, real image for brands, venues, editorial, lifestyle products
- Prefer in-situ photography over abstract gradients or fake 3D renders
- Choose/crop images with stable tonal area for text overlay
- Avoid images with embedded signage/logos/clutter fighting the UI
- Don't generate images with built-in UI frames, splits, cards, or panels
- Use multiple images for multiple moments, not one collage
- First viewport needs a real visual anchor; decorative texture is not enough

### Copy: Product Language

- Write in product language, not design commentary
- Let the headline carry the meaning; supporting copy should be one short sentence
- Cut repetition between sections and words aggressively
- Don't include prompt language or design commentary into the UI

**For Product UI (dashboards, tools, admin):**
- Prioritize orientation, status, action over promise, mood, brand voice
- Start with the working surface: KPIs, charts, filters, tables, status context
- Section headings say what the area is or what user can do there (good: "Selected KPIs", "Plan status", "Search metrics"; avoid aspirational language)
- Supporting text explains scope, behavior, freshness, decision value in one sentence
- If sentence could appear in homepage hero/ad, rewrite it until it sounds like product UI
- **Litmus:** If operator scans only headings and numbers, can they understand the page immediately?

### Motion: Presence and Hierarchy

Use motion to create hierarchy, not noise. Ship 2-3 intentional motions for visually-led work:

1. One entrance sequence (hero reveal)
2. One scroll-linked, sticky, or depth effect
3. One hover, reveal, or layout transition that sharpens affordance

**Motion Rules:**
- Noticeable in a quick recording
- Smooth on mobile; fast and restrained
- Consistent across page
- Removed if ornamental only

**Prefer Framer Motion for:**
- Section reveals
- Shared layout transitions
- Scroll-linked opacity/translate/scale shifts
- Sticky storytelling
- Carousels that advance narrative (not just fill space)
- Menus, drawers, modal presence effects

## Validation checklist

- [ ] Visual thesis written and design aligns with mood/material/energy goal
- [ ] Content plan documented; each section has one job
- [ ] First screen immediately communicates brand/product and promise
- [ ] One strong visual anchor visible in first viewport
- [ ] Hierarchy clear by scanning headlines only (no detailed reading needed)
- [ ] Typography: max 2 typefaces with clear reason for each
- [ ] Color: max 1 accent color (unless product already has defined system)
- [ ] Cards used only when card is the interaction unit; otherwise use sections/lists/dividers
- [ ] No more than one dominant idea per section
- [ ] All text over imagery maintains sufficient contrast (WCAG AA minimum)
- [ ] Imagery is real, narrative, and tonal not just decorative
- [ ] Copy is concise product language without commentary or repetition
- [ ] Motion (if used): enters/scrolls/hovers smoothly, serves hierarchy, not ornamental
- [ ] Responsive design tested: desktop (>1024px), tablet (768-1024px), mobile (<480px)
- [ ] Accessibility checked: tap targets, focus states, aria labels, keyboard nav
- [ ] Would design feel premium if all decorative shadows were removed? (If no, simplify)

## Source of truth

- [design/frontend-design-guidance.md](../../design/frontend-design-guidance.md) — Extended design philosophy
- [CONTRIBUTING.md](../../CONTRIBUTING.md#ui-changes) — UI contribution workflow
- [pi_camera_in_docker/static/css/](../../pi_camera_in_docker/static/css/) — Actual style rules, breakpoints, color system
- [pi_camera_in_docker/templates/](../../pi_camera_in_docker/templates/) — HTML structure and templates
- [PRD-frontend.md](../../PRD-frontend.md) — Feature requirements and design intent
- Figma/Penpot designs (if available in [design/](../../design/))

## Common failure modes and recovery actions

| Failure | Cause | Recovery |
| --- | --- | --- |
| Generic SaaS card grid as first impression | Defaulting to component-first over composition-first | Go back to thesis; design composition first, then identify components needed |
| Beautiful image with weak brand presence | Typography hierarchy too flat; brand subordinated | Increase brand name size/weight; ensure it's loudest text element; crop image to give space |
| Strong headline with no clear action | Missing or unclear CTA | Add explicit CTA button/link; position near headline; test with user scanning time |
| Busy imagery behind text | Image contrast too low or image too complex | Re-crop to stable tonal area; darken overlay if needed; test text contrast ratio (WCAG AA) |
| Sections repeating same mood statement | Content plan not specific enough | Rewrite each section's one job; make each visually and narratively distinct |
| Carousel with no narrative purpose | Filler component | Delete carousel; use single image or grid if multiple moments needed |
| App made of stacked cards instead of layout | Copying SaaS defaults instead of applying restraint | Remove card treatment; use dividers/sections; let workspace breathe; evaluate if each card is necessary |
| Motion feels laggy or janky | Not tested on actual mobile devices | Test on real mobile device (not simulator); profile performance; simplify if needed |
| Too many colors/typefaces | Taste failure / lack of constraint | Count typefaces and colors; remove to 2 and 1; ensure each remaining choice has clear reason |

## Maintenance notes

- Review this skill quarterly; especially when design system, brand guidelines, or component library changes
- Update when new motion libraries (Framer Motion versions) or CSS features (container queries) impact guidelines
- Test guidelines on actual motion-in-ocean interfaces (streaming viewer, management dashboard) to ensure they apply
- Document any project-specific overrides or exceptions (e.g., "motion-in-ocean uses CSS Grid instead of Framer Motion")

---

## Related Skills

- **Before this skill:** [`ui-playwright`](../ui-playwright/SKILL.md) — Audit existing UI to understand current state
- **During design:** [`mermaid-creator`](../mermaid-creator/SKILL.md) — Create diagrams that visualize architecture or workflows
- **Implementation:** `contributor-workflow` (from [CONTRIBUTING.md](../../CONTRIBUTING.md)) — Follow workflow for PR and code review
- **Validation:** [`ui-playwright`](../ui-playwright/SKILL.md) — Re-audit design after implementation
- **Deployment:** `deployment-validation-health-checks` (from skills/README.md) — Ensure design loads correctly in production

## Additional Resources

See `/design/` directory for:
- `webcam-layout.pen` — Streaming viewer design source
- `management-dashboard.pen` — Management UI design source
- `mio/` — Brand guidelines and design tokens
