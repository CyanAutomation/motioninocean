type ManagementTokenStorage = Pick<Storage, "removeItem">;

const LEGACY_MANAGEMENT_API_TOKEN_STORAGE_KEY = "management.apiToken";

/**
 * Keeps the management API bearer token in page memory and removes the legacy
 * localStorage copy so it is not retained across browser sessions.
 */
export function createManagementBearerTokenSession(
  getStorage: () => ManagementTokenStorage | undefined,
) {
  try {
    getStorage()?.removeItem(LEGACY_MANAGEMENT_API_TOKEN_STORAGE_KEY);
  } catch {
    // Storage may be unavailable in private browsing or restricted contexts.
  }

  let token = "";

  return {
    getToken(): string {
      return token;
    },
    setToken(value: string): string {
      token = value.trim();
      return token;
    },
  };
}
