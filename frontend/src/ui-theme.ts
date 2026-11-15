/** Shared theme preference handling for the browser interfaces. */

export type ThemeName = "light" | "dark";

export interface ThemeRoot {
  setAttribute(name: string, value: string): void;
}

export interface ThemeStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

export interface ColorSchemePreference {
  matches: boolean;
  onChange(listener: (matches: boolean) => void): void;
}

export interface ThemeControllerOptions {
  storageKey: string;
  getRoot: () => ThemeRoot;
  getStorage?: () => ThemeStorage | null | undefined;
  getColorPreference?: () => ColorSchemePreference | null | undefined;
  followSystemPreference?: boolean;
  onThemeChange?: (theme: ThemeName) => void;
}

export interface ThemeController {
  applyTheme(theme: string, persistPreference?: boolean): void;
  initializeTheme(): void;
}

/** Resolve a saved theme, falling back to the system preference. */
export function resolveThemePreference(
  storedPreference: string | null | undefined,
  prefersDark: boolean,
): ThemeName {
  const normalizedPreference = storedPreference?.trim().toLocaleLowerCase();
  if (normalizedPreference === "light" || normalizedPreference === "dark") {
    return normalizedPreference;
  }
  return prefersDark ? "dark" : "light";
}

/** Create theme behavior while leaving page-specific updates to a callback. */
export function createThemeController(options: ThemeControllerOptions): ThemeController {
  let hasExplicitThemePreference = false;

  function readStoredPreference(): string | null {
    try {
      return options.getStorage?.()?.getItem(options.storageKey) || null;
    } catch {
      return null;
    }
  }

  function applyTheme(theme: string, persistPreference = true): void {
    const resolvedTheme: ThemeName = theme === "dark" ? "dark" : "light";
    options.getRoot().setAttribute("data-theme", resolvedTheme);
    options.onThemeChange?.(resolvedTheme);

    if (!persistPreference) return;

    hasExplicitThemePreference = true;
    try {
      options.getStorage?.()?.setItem(options.storageKey, resolvedTheme);
    } catch {
      // Ignore local storage failures.
    }
  }

  function initializeTheme(): void {
    const storedPreference = readStoredPreference();
    const hasStoredPreference = storedPreference === "light" || storedPreference === "dark";
    hasExplicitThemePreference = hasStoredPreference;
    const colorPreference = options.followSystemPreference
      ? options.getColorPreference?.()
      : undefined;

    applyTheme(resolveThemePreference(storedPreference, colorPreference?.matches === true), false);

    if (options.followSystemPreference && !hasStoredPreference && colorPreference) {
      colorPreference.onChange((prefersDark) => {
        if (!hasExplicitThemePreference) applyTheme(prefersDark ? "dark" : "light", false);
      });
    }
  }

  return { applyTheme, initializeTheme };
}
