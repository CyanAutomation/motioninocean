import {
  createThemeController,
  type ThemeController,
  type ThemeRoot,
  type ThemeStorage,
} from "./ui-theme.js";

interface ThemeIcon {
  style: { display: string };
}

export interface WebcamThemeControllerOptions {
  getRoot: () => ThemeRoot;
  getStorage?: () => ThemeStorage | null | undefined;
  getIcons: () => { moon: ThemeIcon | null; sun: ThemeIcon | null };
}

/** Create webcam-page theme behavior, including its paired sun and moon icons. */
export function createWebcamThemeController(
  options: WebcamThemeControllerOptions,
): ThemeController {
  return createThemeController({
    storageKey: "webcam.theme",
    getRoot: options.getRoot,
    getStorage: options.getStorage,
    onThemeChange(theme) {
      const icons = options.getIcons();
      if (icons.moon) icons.moon.style.display = theme === "dark" ? "none" : "";
      if (icons.sun) icons.sun.style.display = theme === "dark" ? "" : "none";
    },
  });
}
