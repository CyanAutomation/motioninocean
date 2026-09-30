function asRecord(value) {
    return typeof value === "object" && value !== null ? value : {};
}
/** Submit a settings patch and classify the supported webcam API responses. */
export async function saveSettingsPatch(fetcher, patch) {
    const response = await fetcher("/api/v1/settings", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
    });
    if (response.status === 200) {
        const payload = asRecord(await response.json());
        return { kind: "saved", settings: asRecord(payload.settings) };
    }
    if (response.status === 422) {
        const payload = asRecord(await response.json());
        const modifiedOnRestart = Array.isArray(payload.modified_on_restart)
            ? payload.modified_on_restart
            : null;
        return {
            kind: "restart-required",
            settings: asRecord(payload.settings),
            modifiedOnRestart,
        };
    }
    if (response.status === 400) {
        const payload = asRecord(await response.json());
        const errors = asRecord(payload.validation_errors);
        const message = Object.entries(errors)
            .map(([key, value]) => `${key}: ${value}`)
            .join("\n");
        return { kind: "validation-error", message };
    }
    throw new Error(`HTTP ${response.status}`);
}
