/** Shared theme preference handling for the browser interfaces. */
/** Resolve a saved theme, falling back to the system preference. */
export function resolveThemePreference(storedPreference, prefersDark) {
    const normalizedPreference = storedPreference?.trim().toLocaleLowerCase();
    if (normalizedPreference === "light" || normalizedPreference === "dark") {
        return normalizedPreference;
    }
    return prefersDark ? "dark" : "light";
}
/** Create theme behavior while leaving page-specific updates to a callback. */
export function createThemeController(options) {
    let hasExplicitThemePreference = false;
    function readStoredPreference() {
        try {
            return options.getStorage?.()?.getItem(options.storageKey) || null;
        }
        catch {
            return null;
        }
    }
    function applyTheme(theme, persistPreference = true) {
        const resolvedTheme = theme === "dark" ? "dark" : "light";
        options.getRoot().setAttribute("data-theme", resolvedTheme);
        options.onThemeChange?.(resolvedTheme);
        if (!persistPreference)
            return;
        hasExplicitThemePreference = true;
        try {
            options.getStorage?.()?.setItem(options.storageKey, resolvedTheme);
        }
        catch {
            // Ignore local storage failures.
        }
    }
    function initializeTheme() {
        const storedPreference = readStoredPreference();
        const hasStoredPreference = storedPreference === "light" || storedPreference === "dark";
        hasExplicitThemePreference = hasStoredPreference;
        const colorPreference = options.followSystemPreference
            ? options.getColorPreference?.()
            : undefined;
        applyTheme(resolveThemePreference(storedPreference, colorPreference?.matches === true), false);
        if (options.followSystemPreference && !hasStoredPreference && colorPreference) {
            colorPreference.onChange((prefersDark) => {
                if (!hasExplicitThemePreference)
                    applyTheme(prefersDark ? "dark" : "light", false);
            });
        }
    }
    return { applyTheme, initializeTheme };
}
