interface NavigationElement {
  classList: { toggle(className: string, force?: boolean): void };
  setAttribute?(name: string, value: string): void;
}

export interface ManagementNavigationContext {
  views: Record<string, NavigationElement | null>;
  buttons: Record<string, NavigationElement | null>;
  railButtons: Record<string, Array<NavigationElement | null>>;
  location?: { hash: string };
  history?: { replaceState(state: unknown, title: string, url: string): void };
}

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
export function setActiveView(
  view: string,
  validViews: readonly string[],
  context: ManagementNavigationContext,
): void {
  if (!validViews.includes(view)) return;
  updateViewPanels(context.views, view);
  updateViewButtons(context.buttons, view);
  updateRailButtons(context.railButtons, view);
  updateLocationHash(context, view);
}

function updateViewPanels(views: ManagementNavigationContext["views"], activeView: string): void {
  Object.entries(views).forEach(([name, element]) => {
    if (element) element.classList.toggle("hidden", name !== activeView);
  });
}

function updateViewButtons(
  buttons: ManagementNavigationContext["buttons"],
  activeView: string,
): void {
  Object.entries(buttons).forEach(([name, button]) => {
    if (!button) return;
    const active = name === activeView;
    button.classList.toggle(VIEW_BUTTON_CLASS, active);
    button.setAttribute?.("aria-current", active ? "page" : "false");
  });
}

function updateRailButtons(
  buttons: ManagementNavigationContext["railButtons"],
  activeView: string,
): void {
  Object.entries(buttons).forEach(([name, viewButtons]) => {
    const active = name === activeView;
    viewButtons.forEach((button) => setRailButtonState(button, active));
  });
}

function setRailButtonState(button: NavigationElement | null, active: boolean): void {
  if (!button) return;
  button.classList.toggle(RAIL_BUTTON_CLASS, active);
  button.classList.toggle(MOBILE_RAIL_BUTTON_CLASS, active);
  button.setAttribute?.("aria-current", active ? "page" : "false");
}

function updateLocationHash(context: ManagementNavigationContext, activeView: string): void {
  const nextHash = `#${activeView}`;
  if (context.location?.hash === nextHash) return;
  context.history?.replaceState(null, "", nextHash);
}
