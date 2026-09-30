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
        try {
            const payload = asRecord(await response.json());
            return { kind: "saved", settings: asRecord(payload.settings) };
        }
        catch {
            throw new Error("Failed to parse successful response");
        }
    }
    if (response.status === 422) {
        try {
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
        catch {
            throw new Error("Failed to parse restart-required response");
        }
    }
    if (response.status === 400) {
        try {
            const payload = asRecord(await response.json());
            const errors = asRecord(payload.validation_errors);
            const message = Object.entries(errors)
                .map(([key, value]) => `${key}: ${value}`)
                .join("\n");
            return { kind: "validation-error", message };
        }
        catch {
            return {
                kind: "validation-error",
                message: "Validation failed but could not parse error details",
            };
        }
    }
    throw new Error(`HTTP ${response.status}`);
}
