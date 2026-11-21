import { fileURLToPath } from "node:url";
import path from "node:path";

/**
 * Validate a run ID returned by Soyuz.
 *
 * @param value - The ID in the Soyuz submission response.
 * @returns The validated UUIDv7 run ID.
 * @throws {Error} If the value is not a UUIDv7 string.
 */
export function validateSoyuzRunId(value: unknown): string {
  if (
    typeof value !== "string" ||
    !/^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)
  ) {
    throw new Error("Soyuz returned an invalid UUIDv7 run ID");
  }

  return value;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    console.log(validateSoyuzRunId(process.env.SOYUZ_RUN_ID));
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error(`::error title=Invalid Soyuz run ID::${message}`);
    process.exitCode = 1;
  }
}
