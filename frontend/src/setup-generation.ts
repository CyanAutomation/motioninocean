interface SetupRequestOptions {
  method: string;
  headers: Record<string, string>;
  body: string;
}
type SetupFetch = (
  input: string,
  init: SetupRequestOptions,
) => Promise<Pick<Response, "ok" | "json">>;
type JsonRecord = Record<string, unknown>;

export type SetupGenerationResult =
  | { kind: "validation-error"; errors: string[] }
  | { kind: "generated"; dockerComposeYaml: string; envContent: string };

function asRecord(value: unknown): JsonRecord {
  return typeof value === "object" && value !== null ? (value as JsonRecord) : {};
}

function responseError(payload: unknown, fallback: string): string {
  const error = asRecord(asRecord(payload).error);
  return typeof error.message === "string" && error.message.length > 0 ? error.message : fallback;
}

async function postJson(
  fetcher: SetupFetch,
  path: string,
  config: unknown,
): Promise<Pick<Response, "ok" | "json">> {
  return fetcher(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
}

/** Validate a generated deployment config and request its Docker and env files. */
export async function generateSetupConfiguration(
  config: unknown,
  fetcher: SetupFetch = fetch,
): Promise<SetupGenerationResult> {
  const validationResponse = await postJson(fetcher, "/api/setup/validate", config);
  if (!validationResponse.ok) {
    throw new Error(responseError(await validationResponse.json(), "Validation failed"));
  }

  const validation = asRecord(await validationResponse.json());
  const errors = Array.isArray(validation.errors) ? validation.errors.map(String) : [];
  if (validation.valid === false && errors.length > 0) {
    return { kind: "validation-error", errors };
  }

  const generationResponse = await postJson(fetcher, "/api/setup/generate", config);
  if (!generationResponse.ok) {
    throw new Error(responseError(await generationResponse.json(), "Generation failed"));
  }

  const generated = asRecord(await generationResponse.json());
  return {
    kind: "generated",
    dockerComposeYaml:
      typeof generated.docker_compose_yaml === "string" ? generated.docker_compose_yaml : "",
    envContent: typeof generated.env_content === "string" ? generated.env_content : "",
  };
}
