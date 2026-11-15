import { createThemeController, } from "./ui-theme.js";
/** Create webcam-page theme behavior, including its paired sun and moon icons. */
export function createWebcamThemeController(options) {
    return createThemeController({
        storageKey: "webcam.theme",
        getRoot: options.getRoot,
        getStorage: options.getStorage,
        onThemeChange(theme) {
            const icons = options.getIcons();
            if (icons.moon)
                icons.moon.style.display = theme === "dark" ? "none" : "";
            if (icons.sun)
                icons.sun.style.display = theme === "dark" ? "" : "none";
        },
    });
}
