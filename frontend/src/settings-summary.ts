export type SettingsSchema = Record<
  string,
  | {
      properties?: Record<string, { restartable?: boolean } | undefined>;
    }
  | undefined
>;

export interface SettingsSummaryItem {
  category: string;
  key: string;
  value: unknown;
  envValue: unknown;
  restartable: boolean;
}

export interface SettingsChangesSummary {
  items: SettingsSummaryItem[];
  restartRequired: boolean;
}

interface SettingsOverride {
  category: string;
  key: string;
  value: unknown;
  env_value: unknown;
}

function isSettingsOverride(value: unknown): value is SettingsOverride {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as SettingsOverride).category === "string" &&
    typeof (value as SettingsOverride).key === "string"
  );
}

/** Build the UI summary from the settings override payload and schema. */
export function buildSettingsChangesSummaryModel(
  changesPayload: { overridden?: unknown } | null | undefined,
  schemaPayload: SettingsSchema | null,
): SettingsChangesSummary {
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
