# Webcam Layout Implementability Audit (Current Repo Functionality)

Date: 2026-02-21  
Design source: `design/webcam-layout.pen`

## Scope and Pass Criteria

- Strictness mode: no backend/API changes allowed for a pass.
- Scope: behavior + key UX visuals (status chips/tabs/buttons), excluding decorative-only parity.
- Interpretation: an element is implementable if current repo functionality can support it, even when frontend wiring/restyling is still needed.

## Frame Inventory Audited

1. `bi8Au` — Webcam - Stream - Light Desktop
2. `Al22H` — Webcam - Stream - Dark Desktop
3. `6JpI1` — Webcam - Stream - Light Mobile
4. `xP1lh` — Webcam - Stream - Dark Mobile
5. `qOUtZ` — Webcam - Configuration - Light Desktop
6. `XDIGi` — Webcam - Configuration - Dark Desktop
7. `g0C9s` — Webcam - Configuration - Light Mobile
8. `AAvOe` — Webcam - Configuration - Dark Mobile
9. `t18Jl` — Webcam - Set-Up - Light Desktop
10. `4y5GB` — Webcam - Set-Up - Dark Desktop
11. `trmqY` — Webcam - Set-Up - Light Mobile
12. `WaPlf` — Webcam - Set-Up - Dark Mobile
13. `ggnsE` — Webcam - Runtime Settings - Light Desktop
14. `FoxXg` — Webcam - Runtime Settings - Dark Desktop
15. `pCb6s` — Webcam - Runtime Settings - Light Mobile
16. `cgays` — Webcam - Runtime Settings - Dark Mobile

## Verdict Summary

- `IMPLEMENTABLE_NOW` (already wired): 8 frames
- `IMPLEMENTABLE_WITH_FRONTEND_WIRING` (backend already supports): 8 frames
- `BACKEND_GAP`: 0 frames

Conclusion: all audited frame families are implementable with current repo functionality.  
No backend blockers were found.

## Core Capability Evidence (Backend + Existing UI)

- Stream endpoints and actions exist: `pi_camera_in_docker/modes/webcam.py:733`, `pi_camera_in_docker/modes/webcam.py:751`, `pi_camera_in_docker/modes/webcam.py:768`
- Metrics + status feeds exist: `pi_camera_in_docker/shared.py:333`, `pi_camera_in_docker/shared.py:356`
- Config aggregation (camera/stream/runtime/health) exists: `pi_camera_in_docker/main.py:928`, `pi_camera_in_docker/main.py:861`
- Setup APIs exist (`templates`, `validate`, `generate`): `pi_camera_in_docker/main.py:948`, `pi_camera_in_docker/main.py:974`, `pi_camera_in_docker/main.py:991`
- Settings APIs exist (`GET/PATCH/reset/changes/schema`): `pi_camera_in_docker/settings_api.py:117`, `pi_camera_in_docker/settings_api.py:134`, `pi_camera_in_docker/settings_api.py:161`, `pi_camera_in_docker/settings_api.py:270`, `pi_camera_in_docker/settings_api.py:294`
- Webcam UI already contains Stream/Config/Settings/Set-Up structures: `pi_camera_in_docker/templates/index.html:31`, `pi_camera_in_docker/templates/index.html:149`, `pi_camera_in_docker/templates/index.html:330`, `pi_camera_in_docker/templates/index.html:686`
- Setup wizard behavior is wired end-to-end: `pi_camera_in_docker/static/js/app.js:1453`, `pi_camera_in_docker/static/js/app.js:1830`

## Frame-by-Frame Matrix

| Frame                                  | Key Designed Elements Interrogated                                                                                          | Verdict                              | Why                                                                                                                                                               |
| -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `bi8Au` Stream Light Desktop           | Stream panel, status strip (`Connecting`, `Stream Connected`, `Stale stream`, `Camera inactive`), refresh/fullscreen, stats | `IMPLEMENTABLE_NOW`                  | All behaviors are already wired to `/stream.mjpg` + `/metrics` with state-driven status rendering and controls.                                                   |
| `Al22H` Stream Dark Desktop            | Same as light desktop + dark variant                                                                                        | `IMPLEMENTABLE_WITH_FRONTEND_WIRING` | Behavior exists; dark variant + “Theme Toggle” present in design requires frontend theme-toggle wiring in webcam UI.                                              |
| `6JpI1` Stream Light Mobile            | Mobile stream, refresh/fullscreen compact controls                                                                          | `IMPLEMENTABLE_WITH_FRONTEND_WIRING` | Same stream behavior is available; mobile-specific layout/copy mapping requires frontend restyling only.                                                          |
| `xP1lh` Stream Dark Mobile             | Mobile dark stream + theme affordance                                                                                       | `IMPLEMENTABLE_WITH_FRONTEND_WIRING` | Same as above, with additional theme-toggle wiring requirement in webcam UI.                                                                                      |
| `qOUtZ` Configuration Light Desktop    | Camera settings summary, stream control, health check, refresh-config CTA                                                   | `IMPLEMENTABLE_WITH_FRONTEND_WIRING` | `/api/config` provides all required data; manual “Refresh Config ↻” button in design is not currently explicit but can call existing `updateConfig()`.            |
| `XDIGi` Configuration Dark Desktop     | Same configuration surface + dark variant                                                                                   | `IMPLEMENTABLE_WITH_FRONTEND_WIRING` | Same functional support as light config; dark/theme control requires frontend wiring.                                                                             |
| `g0C9s` Configuration Light Mobile     | Mobile configuration + health legend/check strips                                                                           | `IMPLEMENTABLE_WITH_FRONTEND_WIRING` | Data and health states are available now; compact mobile arrangement and labels need frontend layout work only.                                                   |
| `AAvOe` Configuration Dark Mobile      | Mobile dark configuration + theme affordance                                                                                | `IMPLEMENTABLE_WITH_FRONTEND_WIRING` | Same as light mobile config, with theme-toggle wiring needed.                                                                                                     |
| `t18Jl` Set-Up Light Desktop           | Guided setup stepper, environment/preset/review/generate, output files, previous/next                                       | `IMPLEMENTABLE_NOW`                  | Wizard UI + APIs (`/api/setup/templates`, `/api/setup/validate`, `/api/setup/generate`) are already implemented and connected.                                    |
| `4y5GB` Set-Up Dark Desktop            | Same setup flow + dark variant                                                                                              | `IMPLEMENTABLE_WITH_FRONTEND_WIRING` | Behavior is already complete; dark/theme control parity requires frontend theme-toggle integration for webcam page.                                               |
| `trmqY` Set-Up Light Mobile            | Mobile setup flow and generated output surfaces                                                                             | `IMPLEMENTABLE_WITH_FRONTEND_WIRING` | Endpoints and wizard logic exist; mobile composition and copy harmonization are frontend-only tasks.                                                              |
| `WaPlf` Set-Up Dark Mobile             | Mobile dark setup flow + theme affordance                                                                                   | `IMPLEMENTABLE_WITH_FRONTEND_WIRING` | Same as light mobile setup, plus theme-toggle/frontend dark-state control work.                                                                                   |
| `ggnsE` Runtime Settings Light Desktop | Camera/logging/discovery/feature flags, save/reset, restart messaging, change summary                                       | `IMPLEMENTABLE_WITH_FRONTEND_WIRING` | Settings APIs and schema support all sections. Save/reset/restart-required logic exists; “summary of changes” presentation in design needs additional UI binding. |
| `FoxXg` Runtime Settings Dark Desktop  | Same runtime settings + dark variant                                                                                        | `IMPLEMENTABLE_WITH_FRONTEND_WIRING` | Same functional support as light runtime settings; theme-toggle/state wiring needed for parity.                                                                   |
| `pCb6s` Runtime Settings Light Mobile  | Mobile runtime settings narrative and save flow                                                                             | `IMPLEMENTABLE_WITH_FRONTEND_WIRING` | Backend/settings capability is present; mobile condensed presentation and summary copy require frontend work only.                                                |
| `cgays` Runtime Settings Dark Mobile   | Mobile dark runtime settings + theme affordance                                                                             | `IMPLEMENTABLE_WITH_FRONTEND_WIRING` | Same as light mobile runtime settings, with theme-toggle/frontend dark-state work required.                                                                       |

## Key Cross-Frame Gaps (Frontend-Only, Not Backend)

1. Theme toggle presence/behavior in webcam UI  
   Design includes `Theme Toggle` across frames, but webcam page has no theme control wiring (dark tokens exist in CSS).  
   Evidence: `design/webcam-layout.pen:729`, `pi_camera_in_docker/static/css/theme.css:95`, `pi_camera_in_docker/static/js/management.js:720` (management has pattern), no equivalent in `pi_camera_in_docker/static/js/app.js`.

2. Explicit manual refresh CTA in Configuration frames  
   Design shows a dedicated “Refresh Config ↻” control; current config panel auto-polls every 5 seconds.  
   Evidence: `design/webcam-layout.pen` text includes `Refresh Config ↻`; polling behavior in `pi_camera_in_docker/static/js/app.js:726`, `pi_camera_in_docker/templates/index.html:318`.

3. Runtime “Summary of Changes” visual block is present in template but not populated by settings JS  
   Data path exists (`/api/settings/changes` endpoint), but webcam settings UI currently uses dirty-field/save alerts rather than rendering this block.  
   Evidence: `pi_camera_in_docker/templates/index.html:650`, `pi_camera_in_docker/settings_api.py:294`, no render path in `pi_camera_in_docker/static/js/settings.js`.

## Decision

All UI elements in `webcam-layout.pen` can work with current repo functionality.  
Remaining deltas are frontend implementation/parity tasks, not backend capability gaps.
