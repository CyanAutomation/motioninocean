function isSettingsOverride(value) {
    return (typeof value === "object" &&
        value !== null &&
        typeof value.category === "string" &&
        typeof value.key === "string");
}
/** Build the UI summary from the settings override payload and schema. */
export function buildSettingsChangesSummaryModel(changesPayload, schemaPayload) {
    const overridden = Array.isArray(changesPayload?.overridden)
        ? changesPayload.overridden.filter(isSettingsOverride)
        : [];
    const schemaProperties = schemaPayload || {};
    const items = overridden.map((entry) => {
        const keySchema = schemaProperties[entry.category]?.properties?.[entry.key];
        return {
            category: entry.category,
            key: entry.key,
            value: entry.value,
            envValue: entry.env_value,
            restartable: keySchema?.restartable === true,
        };
    });
    return {
        items,
        restartRequired: items.some((item) => item.restartable),
    };
}
