export interface SetupConfig {
  resolution: string;
  fps: number;
  jpeg_quality: number;
  max_connections: number;
  target_fps: number | null;
  pi3_profile: boolean;
  cors_origins: string;
  mock_camera: boolean;
  auth_token: string;
}

type InputElement = Pick<HTMLElement, "nodeType"> & {
  value?: unknown;
};

interface InputDocument {
  getElementById(id: string): InputElement | null;
}

/**
 * Read and normalize configuration values from the setup wizard form.
 *
 * @param documentRef - Document-like source used to read wizard inputs.
 * @returns Normalized configuration ready for validation or generation.
 */
export function collectSetupConfig(documentRef: InputDocument = document): SetupConfig {
  return {
    resolution: readValue(documentRef, "setup-resolution"),
    fps: readInteger(documentRef, "setup-fps", 0),
    jpeg_quality: readInteger(documentRef, "setup-jpeg-quality", 90),
    max_connections: readInteger(documentRef, "setup-max-connections", 10),
    target_fps: readOptionalInteger(documentRef, "setup-target-fps"),
    pi3_profile: readBoolean(documentRef, "setup-pi3-profile"),
    cors_origins: readValue(documentRef, "setup-cors-origins"),
    mock_camera: readBoolean(documentRef, "setup-mock-camera"),
    auth_token: readValue(documentRef, "setup-auth-token"),
  };
}

function readValue(documentRef: InputDocument, id: string): string {
  const value = documentRef.getElementById(id)?.value;
  return typeof value === "string" ? value : "";
}

function readInteger(documentRef: InputDocument, id: string, fallback: number): number {
  const value = readValue(documentRef, id) || String(fallback);
  return Number.parseInt(value, 10) || fallback;
}

function readOptionalInteger(documentRef: InputDocument, id: string): number | null {
  const value = readValue(documentRef, id);
  return value ? Number.parseInt(value, 10) : null;
}

function readBoolean(documentRef: InputDocument, id: string): boolean {
  return readValue(documentRef, id) === "true";
}
