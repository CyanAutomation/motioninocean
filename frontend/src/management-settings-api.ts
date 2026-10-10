type ResponseShape = Pick<Response, "ok" | "status" | "json">;
interface SettingsRequestOptions {
  method?: string;
  headers?: Record<string, string>;
  body?: string;
}
type SettingsFetcher = (input: string, init?: SettingsRequestOptions) => Promise<ResponseShape>;
type JsonRecord = Record<string, unknown>;

export interface ManagementSettingsPayload extends JsonRecord {
  discovery?: JsonRecord;
}

export interface ManagementSettingsLoadResult {
  settings: ManagementSettingsPayload;
  changes: unknown;
}

export type ManagementSettingsSaveResult =
  | { kind: "saved" }
  | { kind: "restart-required"; modifiedOnRestart: unknown[] }
  | { kind: "failure"; message: string };

function asRecord(value: unknown): JsonRecord {
  return typeof value === "object" && value !== null ? (value as JsonRecord) : {};
}

function asMessage(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

async function parseJsonOrEmpty(response: ResponseShape): Promise<JsonRecord> {
  try {
    return asRecord(await response.json());
  } catch {
    return {};
  }
}

/** Convert management and webcam API errors into operator-facing guidance. */
export function describeManagementApiError(errorPayload: unknown = {}): string {
  const payload = asRecord(errorPayload);
  const error = asRecord(payload.error);
  const code = asMessage(error.code) || asMessage(payload.code);
  const details = asRecord(error.details ?? payload.details);

  if (code === "DISCOVERY_PRIVATE_IP_BLOCKED") {
    return `Discovery registration blocked by private-IP policy. ${asMessage(details.remediation) || "Set MIO_ALLOW_PRIVATE_IPS=true only for trusted internal networks."}`;
  }
  if (code === "WEBCAM_UNAUTHORIZED") {
    return "Token/auth mismatch: the remote webcam rejected credentials. Update this node's webcam bearer token to match WEBCAM_CONTROL_PLANE_AUTH_TOKEN on the webcam node.";
  }
  if (code === "SSRF_BLOCKED") {
    return "Private-IP policy blocked this target. Use a docker network hostname, or explicitly enable MIO_ALLOW_PRIVATE_IPS=true on management for trusted internal networks.";
  }

  return asMessage(error.message) || asMessage(payload.message) || "Request failed.";
}

/** Fetch current management settings and optional override metadata. */
export async function fetchManagementSettings(
  fetcher: SettingsFetcher,
): Promise<ManagementSettingsLoadResult> {
  const [settingsResponse, changesResponse] = await Promise.all([
    fetcher("/api/v1/settings"),
    fetcher("/api/v1/settings/changes"),
  ]);
  if (!settingsResponse.ok) {
    throw new Error("Could not load settings.");
  }

  const settings = asRecord(await settingsResponse.json()) as ManagementSettingsPayload;
  const changes = changesResponse.ok ? await changesResponse.json() : undefined;
  return { settings, changes };
}

/** Save management settings and classify the server response for the UI. */
export async function saveManagementSettings(
  fetcher: SettingsFetcher,
  patchPayload: object,
): Promise<ManagementSettingsSaveResult> {
  try {
    const response = await fetcher("/api/v1/settings", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patchPayload),
    });
    const payload = await parseJsonOrEmpty(response);
    if (response.status === 422) {
      const modifiedOnRestart = Array.isArray(payload.modified_on_restart)
        ? payload.modified_on_restart
        : [];
      return { kind: "restart-required", modifiedOnRestart };
    }
    if (!response.ok) {
      return { kind: "failure", message: describeManagementApiError(payload) };
    }
    return { kind: "saved" };
  } catch (error) {
    return {
      kind: "failure",
      message: error instanceof Error ? error.message : String(error),
    };
  }
}
