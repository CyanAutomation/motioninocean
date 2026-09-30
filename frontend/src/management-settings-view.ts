interface InputControl {
  value: string;
  checked: boolean;
}

interface SettingsControls {
  enabled?: unknown;
  url?: unknown;
  token?: unknown;
  interval?: unknown;
}

interface ManagementSettingsPatch {
  discovery: {
    discovery_enabled: boolean;
    discovery_management_url: string;
    discovery_token: string;
    discovery_interval_seconds: number;
  };
}

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null ? (value as Record<string, unknown>) : {};
}

function isInputControl(value: unknown): value is InputControl {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as InputControl).value === "string" &&
    typeof (value as InputControl).checked === "boolean"
  );
}

/** Fill the management settings controls from API data, applying UI defaults. */
export function hydrateManagementSettingsForm(
  discoverySettings: unknown,
  controls: SettingsControls,
): void {
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
export function buildManagementSettingsPatch(
  controls: SettingsControls,
): ManagementSettingsPatch | null {
  if (
    !isInputControl(controls.enabled) ||
    !isInputControl(controls.url) ||
    !isInputControl(controls.token) ||
    !isInputControl(controls.interval)
  ) {
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
