import { appendFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const SOYUZ_ORIGIN = "https://soyuz.scheimann.workers.dev";

/**
 * Validate and normalize the configured Soyuz service URL.
 *
 * @param value - The value configured as SOYUZ_BASE_URL.
 * @returns The approved Soyuz origin without a trailing slash.
 * @throws {Error} If the value is missing or contains an unexpected origin or URL component.
 */
export function validateSoyuzBaseUrl(value: unknown): string {
  if (typeof value !== "string" || value.length === 0 || /\s/.test(value)) {
    throw new Error(`SOYUZ_BASE_URL must be ${SOYUZ_ORIGIN}`);
  }

  let url: URL;
  try {
    url = new URL(value);
  } catch {
    throw new Error(`SOYUZ_BASE_URL must be ${SOYUZ_ORIGIN}`);
  }

  if (
    url.origin !== SOYUZ_ORIGIN ||
    url.pathname !== "/" ||
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    value.includes("?") ||
    value.includes("#")
  ) {
    throw new Error(`SOYUZ_BASE_URL must be ${SOYUZ_ORIGIN}`);
  }

  return url.origin;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const baseUrl = validateSoyuzBaseUrl(process.env.SOYUZ_BASE_URL);
    if (process.env.GITHUB_ENV) {
      appendFileSync(process.env.GITHUB_ENV, `SOYUZ_BASE_URL=${baseUrl}\n`);
    } else {
      console.log(baseUrl);
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error(`::error title=Invalid Soyuz URL::${message}`);
    process.exitCode = 1;
  }
}
