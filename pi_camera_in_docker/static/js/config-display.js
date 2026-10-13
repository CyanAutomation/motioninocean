/** Reset configuration values and health indicators after a failed refresh. */
export function clearConfigDisplay(document, state, updateConnectionDisplays) {
    const configValues = document.querySelectorAll('[data-config-value="true"]');
    configValues.forEach((element) => {
        element.textContent = "--";
        element.className = "config-value";
        if (element.id.startsWith("config-health-")) {
            element.classList.add("health-indicator", "health-unknown");
            element.setAttribute("data-health-state", "unknown");
        }
        else {
            element.removeAttribute("data-health-state");
        }
        element.removeAttribute("title");
    });
    state.streamConnections.current = "--";
    state.streamConnections.max = "--";
    updateConnectionDisplays();
}
