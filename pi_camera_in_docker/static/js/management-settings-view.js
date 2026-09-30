function asRecord(value) {
    return typeof value === "object" && value !== null ? value : {};
}
function isInputControl(value) {
    return (typeof value === "object" &&
        value !== null &&
        typeof value.value === "string" &&
        typeof value.checked === "boolean");
}
/** Fill the management settings controls from API data, applying UI defaults. */
export function hydrateManagementSettingsForm(discoverySettings, controls) {
    const settings = asRecord(discoverySettings);
    if (isInputControl(controls.enabled)) {
        controls.enabled.checked = Boolean(settings.discovery_enabled);
    }
    if (isInputControl(controls.url)) {
        controls.url.value = String(settings.discovery_management_url || "");
    }
    if (isInputControl(controls.token)) {
        controls.token.value = String(settings.discovery_token || "");
    }
    if (isInputControl(controls.interval)) {
        controls.interval.value = String(settings.discovery_interval_seconds ?? 30);
    }
}
/** Build a normalized PATCH body only when all discovery controls are available. */
export function buildManagementSettingsPatch(controls) {
    if (!isInputControl(controls.enabled) ||
        !isInputControl(controls.url) ||
        !isInputControl(controls.token) ||
        !isInputControl(controls.interval)) {
        return null;
    }
    return {
        discovery: {
            discovery_enabled: controls.enabled.checked,
            discovery_management_url: controls.url.value.trim(),
            discovery_token: controls.token.value.trim(),
            discovery_interval_seconds: Number(controls.interval.value || "30"),
        },
    };
}
