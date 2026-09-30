function hydrateValueControl(control, value, updateSlider) {
    if (!control)
        return;
    control.value = String(value);
    if (updateSlider)
        updateSlider(control);
}
function hydrateCheckboxControl(control, value) {
    if (!control)
        return;
    control.checked = value === true;
}
/** Populate camera controls from API values, preserving valid zero values. */
export function hydrateCameraSettingsForm(settings, dependencies) {
    hydrateValueControl(dependencies.getValueControl("setting-resolution"), settings.resolution || "");
    hydrateValueControl(dependencies.getValueControl("setting-fps"), settings.fps ?? 30, dependencies.updateSlider);
    hydrateValueControl(dependencies.getValueControl("setting-jpeg-quality"), settings.jpeg_quality ?? 85, dependencies.updateSlider);
    hydrateValueControl(dependencies.getValueControl("setting-max-connections"), settings.max_stream_connections ?? 2);
    hydrateValueControl(dependencies.getValueControl("setting-max-frame-age"), settings.max_frame_age_seconds ?? 10);
}
/** Populate discovery controls from API values with UI defaults. */
export function hydrateDiscoverySettingsForm(settings, dependencies) {
    hydrateCheckboxControl(dependencies.getCheckboxControl("setting-discovery-enabled"), settings.discovery_enabled);
    hydrateValueControl(dependencies.getValueControl("setting-discovery-url"), settings.discovery_management_url || "http://127.0.0.1:8001");
    hydrateValueControl(dependencies.getValueControl("setting-discovery-token"), settings.discovery_token || "");
    hydrateValueControl(dependencies.getValueControl("setting-discovery-interval"), settings.discovery_interval_seconds ?? 30);
}
