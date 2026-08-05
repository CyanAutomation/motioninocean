/** Pure management-dashboard status and error domain helpers. */
export const STATUS_SUBTYPE_CONFIG = {
    unsupported_transport: {
        label: "Unsupported transport",
        helpText: "Configured transport is not supported by the target node.",
        statusClass: "ui-status-pill--error",
    },
    unauthorized: {
        label: "Unauthorized",
        helpText: "Credentials were rejected by the webcam API.",
        statusClass: "ui-status-pill--error",
    },
    no_response: {
        label: "No response",
        helpText: "Node did not return a valid status response.",
        statusClass: "ui-status-pill--error",
    },
    partial_probe: {
        label: "Partial probe",
        helpText: "Node responded, but readiness or probe checks are incomplete.",
        statusClass: "ui-status-pill--neutral",
    },
    degraded: {
        label: "Degraded",
        helpText: "Node is reachable but reports a degraded state.",
        statusClass: "ui-status-pill--neutral",
    },
    healthy: {
        label: "Healthy",
        helpText: "Node is ready and healthy.",
        statusClass: "ui-status-pill--success",
    },
};
export function statusClass(statusText) {
    const normalized = (statusText || "unknown").toLowerCase();
    if (["ok", "healthy", "ready"].includes(normalized)) {
        return "ui-status-pill--success";
    }
    if (["error", "down", "failed", "unhealthy"].includes(normalized)) {
        return "ui-status-pill--error";
    }
    return "ui-status-pill--neutral";
}
export function normalizeWebcamStatusError(error = {}) {
    return {
        status: "error",
        stream_available: false,
        error_code: error.code || "UNKNOWN_ERROR",
        error_message: error.message || "Node status request failed.",
        error_details: error.details || null,
    };
}
export function isFailureStatus(status = {}) {
    if (status.error_code) {
        return true;
    }
    const normalized = String(status.status || "unknown").toLowerCase();
    return ["error", "failed", "down", "unhealthy", "unauthorized"].includes(normalized);
}
