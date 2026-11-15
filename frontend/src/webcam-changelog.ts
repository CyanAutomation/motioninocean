import { escapeHtml } from "./html.js";

export interface ChangelogEntry {
  changes: string[];
  release_date: string | null;
  version: string;
}

export interface ChangelogPayload {
  entries: ChangelogEntry[];
  full_changelog_url?: string;
  message?: string;
  source?: string;
  status: string;
}

const MAX_VISIBLE_ENTRIES = 3;

/** Render changelog entries as release cards for the utility modal. */
export function renderChangelogHtml(
  payload: ChangelogPayload,
  debugModeEnabled: boolean,
): string {
  const entries = Array.isArray(payload.entries) ? payload.entries : [];
  const visibleEntries = entries.slice(0, MAX_VISIBLE_ENTRIES);
  const cardsHtml = visibleEntries
    .map((entry) => {
      const releaseDate = entry.release_date || "Unknown date";
      const releaseTitle = `v${entry.version}`;
      const changes = Array.isArray(entry.changes) ? entry.changes : [];
      const itemsHtml =
        changes.length > 0
          ? changes.map((change) => `<li>${escapeHtml(change)}</li>`).join("")
          : "<li>No release notes available.</li>";

      return [
        '<article class="changelog-card">',
        `<h3>${escapeHtml(releaseTitle)}</h3>`,
        `<p class="utility-subtle">${escapeHtml(releaseDate)}</p>`,
        `<ul>${itemsHtml}</ul>`,
        "</article>",
      ].join("");
    })
    .join("");

  const statusNote =
    payload.status === "degraded" ? renderDegradedChangelogNote(payload, debugModeEnabled) : "";
  const fullChangelogUrl =
    typeof payload.full_changelog_url === "string" ? payload.full_changelog_url.trim() : "";
  const safeFullChangelogUrl = getSafeExternalUrl(fullChangelogUrl);
  const fullChangelogLink = safeFullChangelogUrl
    ? `<p><a href="${escapeHtml(safeFullChangelogUrl)}" target="_blank" rel="noopener noreferrer">View full changelog</a></p>`
    : "";

  return [
    '<section class="changelog-list">',
    statusNote,
    cardsHtml || "<p>No changelog entries available.</p>",
    fullChangelogLink,
    "</section>",
  ].join("");
}

function getSafeExternalUrl(value: string): string | null {
  if (!value) return null;

  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:" ? url.href : null;
  } catch {
    return null;
  }
}

function renderDegradedChangelogNote(
  payload: Pick<ChangelogPayload, "message" | "source">,
  debugModeEnabled: boolean,
): string {
  const userFriendlyMessage =
    "We couldn't load the latest changelog details right now. Try again shortly.";
  if (!debugModeEnabled) {
    return `<p class="utility-subtle">${escapeHtml(userFriendlyMessage)}</p>`;
  }

  const debugDetails = [payload.message, payload.source].filter(Boolean).join(" | ");
  const debugLine = debugDetails
    ? `<br><span class="utility-subtle">Debug: ${escapeHtml(debugDetails)}</span>`
    : "";
  return `<p class="utility-subtle">${escapeHtml(userFriendlyMessage)}${debugLine}</p>`;
}
