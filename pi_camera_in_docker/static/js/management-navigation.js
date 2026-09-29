const VIEW_BUTTON_CLASS = "management-view-btn--active";
const RAIL_BUTTON_CLASS = "rail-btn--active";
const MOBILE_RAIL_BUTTON_CLASS = "mobile-rail-btn--active";
/**
 * Activate a management view and synchronize its controls and location hash.
 *
 * @param view - Requested view key.
 * @param validViews - View keys accepted by the dashboard.
 * @param context - Panel, button, location, and history references.
 * @returns Nothing.
 */
export function setActiveView(view, validViews, context) {
    if (!validViews.includes(view))
        return;
    updateViewPanels(context.views, view);
    updateViewButtons(context.buttons, view);
    updateRailButtons(context.railButtons, view);
    updateLocationHash(context, view);
}
function updateViewPanels(views, activeView) {
    Object.entries(views).forEach(([name, element]) => {
        if (element)
            element.classList.toggle("hidden", name !== activeView);
    });
}
function updateViewButtons(buttons, activeView) {
    Object.entries(buttons).forEach(([name, button]) => {
        if (!button)
            return;
        const active = name === activeView;
        button.classList.toggle(VIEW_BUTTON_CLASS, active);
        button.setAttribute?.("aria-current", active ? "page" : "false");
    });
}
function updateRailButtons(buttons, activeView) {
    Object.entries(buttons).forEach(([name, viewButtons]) => {
        const active = name === activeView;
        viewButtons.forEach((button) => setRailButtonState(button, active));
    });
}
function setRailButtonState(button, active) {
    if (!button)
        return;
    button.classList.toggle(RAIL_BUTTON_CLASS, active);
    button.classList.toggle(MOBILE_RAIL_BUTTON_CLASS, active);
    button.setAttribute?.("aria-current", active ? "page" : "false");
}
function updateLocationHash(context, activeView) {
    const nextHash = `#${activeView}`;
    if (context.location?.hash === nextHash)
        return;
    context.history?.replaceState(null, "", nextHash);
}
