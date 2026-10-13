export interface ConfigDisplayValue {
  id: string;
  textContent: string | null;
  className: string;
  classList: Pick<DOMTokenList, "add">;
  setAttribute(name: string, value: string): void;
  removeAttribute(name: string): void;
}

export interface ConfigDisplayDocument {
  querySelectorAll(selector: string): {
    forEach(callback: (element: ConfigDisplayValue) => void): void;
  };
}

export interface ConfigDisplayState {
  streamConnections: { current: string; max: string };
}

/** Reset configuration values and health indicators after a failed refresh. */
export function clearConfigDisplay(
  document: ConfigDisplayDocument,
  state: ConfigDisplayState,
  updateConnectionDisplays: () => void,
): void {
  const configValues = document.querySelectorAll('[data-config-value="true"]');
  configValues.forEach((element) => {
    element.textContent = "--";
    element.className = "config-value";
    if (element.id.startsWith("config-health-")) {
      element.classList.add("health-indicator", "health-unknown");
      element.setAttribute("data-health-state", "unknown");
    } else {
      element.removeAttribute("data-health-state");
    }
    element.removeAttribute("title");
  });

  state.streamConnections.current = "--";
  state.streamConnections.max = "--";
  updateConnectionDisplays();
}
