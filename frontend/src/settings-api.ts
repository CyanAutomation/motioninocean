type SaveSettingsResponse = Pick<Response, "status" | "json">;
type SettingsPatchPayload = Record<string, Record<string, unknown>>;

interface SettingsRequestOptions {
  method: string;
  headers: Record<string, string>;
  body: string;
}

interface SettingsSnapshot {
  [category: string]: Record<string, unknown> | undefined;
}

type SettingsSaveResult =
  | { kind: "saved"; settings: SettingsSnapshot }
  | {
      kind: "restart-required";
      settings: SettingsSnapshot;
      modifiedOnRestart: unknown[] | null;
    }
  | { kind: "validation-error"; message: string };

type SettingsFetcher = (
  input: string,
  init: SettingsRequestOptions,
) => Promise<SaveSettingsResponse>;

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null ? (value as Record<string, unknown>) : {};
}

/** Submit a settings patch and classify the supported webcam API responses. */
export async function saveSettingsPatch(
  fetcher: SettingsFetcher,
  patch: SettingsPatchPayload,
): Promise<SettingsSaveResult> {
  const response = await fetcher("/api/v1/settings", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });

  if (response.status === 200) {
    const payload = asRecord(await response.json());
    return { kind: "saved", settings: asRecord(payload.settings) as SettingsSnapshot };
  }

  if (response.status === 422) {
    const payload = asRecord(await response.json());
    const modifiedOnRestart = Array.isArray(payload.modified_on_restart)
      ? payload.modified_on_restart
      : null;
    return {
      kind: "restart-required",
      settings: asRecord(payload.settings) as SettingsSnapshot,
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
