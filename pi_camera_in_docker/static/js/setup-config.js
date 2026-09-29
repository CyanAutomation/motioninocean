/**
 * Read and normalize configuration values from the setup wizard form.
 *
 * @param documentRef - Document-like source used to read wizard inputs.
 * @returns Normalized configuration ready for validation or generation.
 */
export function collectSetupConfig(documentRef = document) {
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
function readValue(documentRef, id) {
    return documentRef.getElementById(id)?.value || "";
}
function readInteger(documentRef, id, fallback) {
    const value = readValue(documentRef, id) || String(fallback);
    return Number.parseInt(value, 10) || fallback;
}
function readOptionalInteger(documentRef, id) {
    const value = readValue(documentRef, id);
    return value ? Number.parseInt(value, 10) : null;
}
function readBoolean(documentRef, id) {
    return readValue(documentRef, id) === "true";
}
