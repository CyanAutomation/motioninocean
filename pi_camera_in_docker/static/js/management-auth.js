const LEGACY_MANAGEMENT_API_TOKEN_STORAGE_KEY = "management.apiToken";
/**
 * Keeps the management API bearer token in page memory and removes the legacy
 * localStorage copy so it is not retained across browser sessions.
 */
export function createManagementBearerTokenSession(getStorage) {
    try {
        getStorage()?.removeItem(LEGACY_MANAGEMENT_API_TOKEN_STORAGE_KEY);
    }
    catch {
        // Storage may be unavailable in private browsing or restricted contexts.
    }
    let token = "";
    return {
        getToken() {
            return token;
        },
        setToken(value) {
            token = value.trim();
            return token;
        },
    };
}
