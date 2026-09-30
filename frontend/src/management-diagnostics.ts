export type DiagnosticState = "pass" | "warn" | "fail";

export type DiagnosticCheck = Record<string, unknown>;

export interface DiagnosticChecks {
  registration?: DiagnosticCheck;
  url_validation?: DiagnosticCheck;
  dns_resolution?: DiagnosticCheck;
  network_connectivity?: DiagnosticCheck;
  api_endpoint?: DiagnosticCheck;
}

export interface DiagnosticRow {
  key: string;
  state: DiagnosticState;
  detail: string;
  meta: string;
}

export interface DiagnosticSummary {
  label: string;
  className: string;
  state: DiagnosticState;
}

export interface DiagnosticBanner {
  interpretation: string;
  cta: string;
}

const VALID_STATES = new Set<DiagnosticState>(["pass", "warn", "fail"]);

function checkValue(diagnostics: DiagnosticChecks, key: keyof DiagnosticChecks): DiagnosticCheck {
  const value = diagnostics[key];
  return value && typeof value === "object" ? value : {};
}

function textValue(check: DiagnosticCheck, key: string): string {
  const value = check[key];
  return typeof value === "string" || typeof value === "number" ? String(value) : "";
}

function codeMeta(check: DiagnosticCheck): string {
  const code = textValue(check, "code");
  return code ? `Code: ${code}` : "";
}

function resolvedIpMeta(check: DiagnosticCheck): string {
  const ips = check.resolved_ips;
  if (!Array.isArray(ips) || ips.length === 0) {
    return "";
  }
  return `IPs: ${ips.map(String).join(", ")}`;
}

function statusFor(check: DiagnosticCheck, fallback: () => DiagnosticState): DiagnosticState {
  const state = textValue(check, "status").toLowerCase();
  return VALID_STATES.has(state as DiagnosticState) ? (state as DiagnosticState) : fallback();
}

function diagnosticRow(
  key: string,
  check: DiagnosticCheck,
  fallback: (value: DiagnosticCheck) => DiagnosticState,
  detail: (value: DiagnosticCheck) => string,
  meta: (value: DiagnosticCheck) => string = codeMeta,
): DiagnosticRow {
  return {
    key,
    state: statusFor(check, () => fallback(check)),
    detail: detail(check),
    meta: meta(check),
  };
}

/**
 * Normalize diagnostic payloads into rows used by the dashboard and text report.
 *
 * Structured statuses take precedence over derived booleans. Missing and malformed checks
 * receive conservative fallback states and readable details.
 *
 * @param diagnostics - Diagnostic checks returned by the management API.
 * @returns Stable rows for each diagnostic check.
 */
export function getDiagnosticCheckRows(diagnostics: DiagnosticChecks = {}): DiagnosticRow[] {
  const registration = checkValue(diagnostics, "registration");
  const urlValidation = checkValue(diagnostics, "url_validation");
  const dns = checkValue(diagnostics, "dns_resolution");
  const network = checkValue(diagnostics, "network_connectivity");
  const api = checkValue(diagnostics, "api_endpoint");

  return [
    diagnosticRow(
      "Registration",
      registration,
      (value) => (value.valid ? "pass" : "fail"),
      (value) =>
        value.valid
          ? "Node registration is valid."
          : textValue(value, "error") || "Registration data is invalid.",
    ),
    diagnosticRow(
      "URL validation",
      urlValidation,
      (value) => (value.blocked ? "fail" : "pass"),
      (value) =>
        value.blocked
          ? textValue(value, "blocked_reason") || "URL blocked by policy."
          : "Base URL passed validation.",
    ),
    diagnosticRow(
      "DNS resolution",
      dns,
      (value) => (value.resolves ? "pass" : "fail"),
      (value) =>
        value.resolves
          ? "DNS lookup succeeded."
          : textValue(value, "error") || "DNS lookup failed.",
      resolvedIpMeta,
    ),
    diagnosticRow(
      "Network connectivity",
      network,
      (value) => (value.reachable ? "pass" : "fail"),
      (value) =>
        value.reachable
          ? "Node is reachable over the network."
          : textValue(value, "error") || "Could not reach node.",
      (value) =>
        [
          textValue(value, "category") && `Category: ${textValue(value, "category")}`,
          codeMeta(value),
        ]
          .filter(Boolean)
          .join(" · "),
    ),
    diagnosticRow(
      "API endpoint",
      api,
      (value) => (value.accessible === false ? "fail" : value.healthy === false ? "warn" : "pass"),
      (value) =>
        value.status_code
          ? `HTTP ${String(value.status_code)}`
          : textValue(value, "error") || "Endpoint check incomplete.",
      (value) =>
        [
          value.healthy === false && value.status_code === 503
            ? "Node reachable but may still be initializing."
            : "",
          codeMeta(value),
        ]
          .filter(Boolean)
          .join(" · "),
    ),
  ];
}

/**
 * Derive the overall diagnostic state from the individual check rows.
 *
 * @param checkRows - Normalized diagnostic rows.
 * @returns A summary label, CSS class, and state.
 */
export function getDiagnosticSummaryState(
  checkRows: readonly DiagnosticRow[] = [],
): DiagnosticSummary {
  if (checkRows.some((row) => row.state === "fail")) {
    return { label: "Action required", className: "diagnostic-pill--fail", state: "fail" };
  }

  const warningRows = checkRows.filter((row) => row.state === "warn");
  if (warningRows.length === 0) {
    return { label: "Healthy", className: "diagnostic-pill--pass", state: "pass" };
  }

  const transientWarningKeys = new Set(["API endpoint"]);
  const onlyTransientWarnings = warningRows.every((row) => transientWarningKeys.has(row.key));
  return {
    label: onlyTransientWarnings ? "Warning" : "Action recommended",
    className: "diagnostic-pill--warn",
    state: "warn",
  };
}

/**
 * Build operator guidance from the network category and diagnostic error code.
 *
 * @param category - Network failure category from the diagnostic response.
 * @param diagnostics - Full diagnostic check payload.
 * @returns A short remediation instruction.
 */
export function getConnectivityRemediation(
  category: string,
  diagnostics: DiagnosticChecks = {},
): string {
  const network = checkValue(diagnostics, "network_connectivity");
  const url = checkValue(diagnostics, "url_validation");
  const code = textValue(network, "code") || textValue(url, "code");
  const codeText = code ? ` (${code})` : "";
  const categoryMessages: Record<string, string> = {
    timeout: `Node connection timed out${codeText}. Retry in 30s while the service finishes startup.`,
    tls: `TLS handshake failed${codeText}. Verify certificates or switch the webcam base URL to http:// if TLS is not configured.`,
    dns: `Hostname could not be resolved${codeText}. Check the webcam base URL hostname and DNS configuration.`,
    connection_refused_or_reset: `Connection was refused${codeText}. Confirm the webcam process is running and listening on the configured port.`,
    network: `Network path is blocked${codeText}. Check firewall, routing, and container network settings.`,
    ssrf_blocked: `SSRF protection blocked this target${codeText}. Use an allowed hostname or update private-IP policy for trusted networks.`,
  };

  if (categoryMessages[category]) {
    return categoryMessages[category];
  }
  if (code === "SSRF_BLOCKED") {
    return `SSRF protection blocked this target${codeText}. Update webcam base URL to an allowed address or relax policy for trusted private networks.`;
  }
  return "Review check details below to resolve connectivity issues.";
}

/**
 * Choose the summary banner text and primary action for the current diagnostics.
 *
 * @param summary - Overall diagnostic state.
 * @param checkRows - Normalized diagnostic rows.
 * @param diagnostics - Full diagnostic check payload.
 * @returns User-facing interpretation and call to action.
 */
export function getDiagnosticSummaryBanner(
  summary: DiagnosticSummary,
  checkRows: readonly DiagnosticRow[] = [],
  diagnostics: DiagnosticChecks = {},
): DiagnosticBanner {
  if (summary.state === "pass") {
    return {
      interpretation: "All diagnostic checks passed; this webcam appears healthy and reachable.",
      cta: "No action needed",
    };
  }

  const apiWarning = checkRows.some((row) => row.key === "API endpoint" && row.state === "warn");
  if (summary.state === "warn" && apiWarning) {
    return {
      interpretation: "Connectivity looks good, but the webcam API is still warming up.",
      cta: "Retry in 30s",
    };
  }

  const url = checkValue(diagnostics, "url_validation");
  if (textValue(url, "code") === "SSRF_BLOCKED") {
    return {
      interpretation: getConnectivityRemediation("ssrf_blocked", diagnostics),
      cta: "Update webcam base URL",
    };
  }

  const network = checkValue(diagnostics, "network_connectivity");
  const category = textValue(network, "category");
  const networkActions: Record<string, string> = {
    tls: "Update webcam base URL",
    dns: "Update webcam base URL",
    timeout: "Retry in 30s",
    connection_refused_or_reset: "Update webcam base URL",
    network: "Update webcam base URL",
  };
  if (networkActions[category]) {
    return {
      interpretation: getConnectivityRemediation(category, diagnostics),
      cta: networkActions[category],
    };
  }

  const registration = checkValue(diagnostics, "registration");
  if (textValue(registration, "code") === "WEBCAM_UNAUTHORIZED") {
    return {
      interpretation:
        "Node authentication failed. The configured webcam bearer token does not match WEBCAM_CONTROL_PLANE_AUTH_TOKEN on the node.",
      cta: "Set auth token",
    };
  }

  return {
    interpretation:
      "One or more checks need remediation before this webcam can be considered healthy.",
    cta: "Review recommendations",
  };
}
