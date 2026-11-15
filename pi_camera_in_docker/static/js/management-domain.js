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
/** Normalize discovery metadata for display and filtering. */
export function getDiscoveryInfo(webcam = {}) {
    const discovery = webcam.discovery || {};
    const source = discovery.source || "manual";
    const firstSeen = discovery.first_seen || webcam.last_seen || null;
    const lastAnnounceAt = discovery.last_announce_at || null;
    const approved = source === "discovered" ? discovery.approved === true : true;
    return { source, firstSeen, lastAnnounceAt, approved };
}
/** Format an ISO date for display, preserving invalid source text for diagnostics. */
export function formatDateTime(isoString) {
    if (!isoString)
        return "—";
    const parsed = new Date(isoString);
    if (Number.isNaN(parsed.getTime()))
        return isoString;
    return parsed.toLocaleString();
}
/** Format the aggregated node status history for the details row. */
export function formatAggregationDetails(status = {}) {
    const fragments = [];
    if (status.last_success_at) {
        fragments.push(`Last success: ${formatDateTime(status.last_success_at)}`);
    }
    if (status.first_failure_at) {
        fragments.push(`First failure: ${formatDateTime(status.first_failure_at)}`);
    }
    if (typeof status.consecutive_failures === "number" && status.consecutive_failures > 0) {
        fragments.push(`Consecutive failures: ${status.consecutive_failures}`);
    }
    return fragments.join(" • ");
}
/** Convert API status fields into the labels and explanation shown in the node table. */
export function normalizeWebcamStatusForUi(status = {}) {
    const statusText = String(status.status || "unknown").toLowerCase();
    const errorCode = String(status.error_code || "").toUpperCase();
    const isReady = status.ready === true;
    const subtype = getWebcamStatusSubtype(statusText, errorCode, isReady);
    const config = STATUS_SUBTYPE_CONFIG[subtype] || {
        label: "Unknown",
        helpText: "Node state is unknown.",
        statusClass: statusClass(statusText),
    };
    let reasonText = getStatusReason(status);
    if (subtype === "healthy") {
        reasonText = "Ready and responding.";
    }
    else if (subtype === "partial_probe") {
        reasonText = String(status.error_message || "Node responded, but readiness is incomplete.");
    }
    else if (subtype === "degraded") {
        reasonText = String(status.error_message || "Node is reachable, but operating in a degraded mode.");
    }
    return {
        subtype,
        label: config.label,
        helpText: config.helpText,
        statusClass: config.statusClass,
        reasonText,
    };
}
function getStatusReason(status = {}) {
    const code = status.error_code;
    const knownReasons = {
        SSRF_BLOCKED: {
            title: "Private-IP policy blocked this webcam target.",
            hint: "Use a docker network hostname (e.g., 'motion-in-ocean-webcam:8000') or explicitly set MIO_ALLOW_PRIVATE_IPS=true on management for trusted internal networks. Click Diagnose for details.",
        },
        NETWORK_UNREACHABLE: {
            title: "Node is unreachable on the network.",
            hint: "Check webcam is running, network connectivity, and firewall rules. Click Diagnose for details.",
        },
        DOCKER_PROXY_UNREACHABLE: {
            title: "Docker proxy is unreachable.",
            hint: "Verify docker-socket-proxy is running and accessible on configured host and port. Click Diagnose for details.",
        },
        DOCKER_CONTAINER_NOT_FOUND: {
            title: "Container not found on docker proxy.",
            hint: "Verify the container ID/name is correct and running on the docker host.",
        },
        DOCKER_API_ERROR: {
            title: "Docker API returned an error.",
            hint: "Check docker proxy configuration and container status.",
        },
        INVALID_DOCKER_URL: {
            title: "Docker URL is invalid.",
            hint: "Use format: docker://proxy-hostname:port/container-id",
        },
        WEBCAM_UNREACHABLE: {
            title: "Node is unreachable.",
            hint: "Check the webcam base URL, networking, and that the webcam service is running.",
        },
        WEBCAM_UNAUTHORIZED: {
            title: "Token/auth mismatch with remote node.",
            hint: "Set this webcam bearer token to match WEBCAM_CONTROL_PLANE_AUTH_TOKEN on the remote webcam, then refresh.",
        },
        WEBCAM_INVALID_RESPONSE: {
            title: "Node returned an invalid response.",
            hint: "Verify the webcam API version and status endpoint compatibility.",
        },
        TRANSPORT_UNSUPPORTED: {
            title: "Configured transport is unsupported.",
            hint: "Switch to a supported transport for this node.",
        },
        WEBCAM_API_MISMATCH: {
            title: "Node API does not match expected management endpoints.",
            hint: "Confirm the webcam is running the compatible management service and exposes /api/status.",
        },
    };
    const reason = typeof code === "string" ? knownReasons[code] : undefined;
    if (reason)
        return `${reason.title} ${reason.hint}`;
    if (status.error_message)
        return String(status.error_message);
    return "No additional details available.";
}
function getWebcamStatusSubtype(statusText, errorCode, isReady) {
    if (errorCode === "TRANSPORT_UNSUPPORTED")
        return "unsupported_transport";
    if (errorCode === "WEBCAM_UNAUTHORIZED" || statusText === "unauthorized") {
        return "unauthorized";
    }
    if (["ok", "healthy", "ready"].includes(statusText)) {
        return isReady ? "healthy" : "partial_probe";
    }
    if (["degraded", "warning"].includes(statusText))
        return "degraded";
    if (["partial", "probing"].includes(statusText))
        return "partial_probe";
    return "no_response";
}
