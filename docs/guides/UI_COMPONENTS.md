# Frontend UI primitives

Motion In Ocean's framework-free UI primitives are used by the management dashboard and can be reused by other pages. They live in `pi_camera_in_docker/static/css/ui-primitives.css` and `frontend/src/ui-components.ts`; browser JavaScript is generated from TypeScript.

## Layout and display

- `.ui-app-shell`, `.ui-app-shell__header`, `.ui-app-shell__navigation`, and `.ui-app-shell__main` provide a responsive application shell.
- `.ui-sidebar`, `.ui-sidebar__list`, and `.ui-sidebar__link` provide labeled navigation. Set `aria-current="page"` on the active destination.
- `.ui-page-header` groups the current view title, description, and immediate actions.
- `.ui-toolbar` and `.ui-toolbar__group` align search, filters, and related controls.
- `.ui-settings-group`, `.ui-settings-list`, and `.ui-settings-row` group preferences with their labels and descriptions.
- `.ui-badge` variants communicate success, warning, danger, and neutral states. Keep the visible state label so color is never the only cue.
- `.ui-feedback--error` and `.ui-feedback--success` provide semantic feedback colors using the application theme tokens.
- `.ui-dialog` styles native modal dialogs; use `<dialog>.showModal()` and a visible Cancel or Close action.

The primitives use the existing semantic theme variables. They also provide visible keyboard focus, narrow-screen reflow, reduced-motion handling, and forced-colors boundaries. Application-specific layout and behavior remain owned by the consuming page.

## TypeScript helpers

`frontend/src/ui-components.ts` exports reusable behavior alongside the CSS:

- `filterCollectionRows(rows, query, status)` filters table rows using `data-search` and `data-status`, updates each row's `hidden` state, and returns the visible count.
- `resolveThemePreference(storedPreference, prefersDark)` chooses an explicit saved theme or falls back to the operating system preference.
- `setFeedbackMessage(element, message, tone)` updates accessible feedback copy and its semantic visual tone.
- `confirmInDialog(dialog, options)` fills and opens the shared native confirmation dialog. It resolves `true` only when the user confirms; Cancel and Escape resolve `false`.

Use these primitives for new screens before adding page-specific equivalents. Keep actions, API calls, form rules, and data models in the feature module.
