/**
 * Fetch and normalize the README help payload returned by the application API.
 *
 * @param fetcher - Fetch implementation used to request the help endpoint.
 * @returns The normalized README payload.
 * @throws {Error} When the request fails and the API did not return degraded content.
 */
export async function fetchReadmeContent(fetcher = fetch) {
    const response = await fetcher("/api/help/readme", {
        headers: { Accept: "application/json, text/plain" },
    });
    const payload = await readJsonPayload(response);
    const normalizedPayload = normalizeReadmePayload(payload, response.ok);
    if (!response.ok && normalizedPayload.status !== "degraded") {
        throw new Error(normalizedPayload.message || "Failed to load help documentation");
    }
    return normalizedPayload;
}
async function readJsonPayload(response) {
    try {
        const payload = await response.json();
        return isRecord(payload) ? payload : {};
    }
    catch {
        return {};
    }
}
function normalizeReadmePayload(payload, responseOk) {
    return {
        status: nonEmptyString(payload.status) || (responseOk ? "ok" : "error"),
        content: stringValue(payload.content),
        message: nonEmptyString(payload.message) || (responseOk ? "" : "Failed to load help documentation"),
        documentation_url: stringValue(payload.documentation_url),
        source: stringValue(payload.source),
    };
}
function isRecord(value) {
    return typeof value === "object" && value !== null;
}
function nonEmptyString(value) {
    return typeof value === "string" && value.trim() ? value : "";
}
function stringValue(value) {
    return typeof value === "string" ? value : "";
}
/** Render the README's supported Markdown subset to HTML for sanitization. */
/**
 * Render the README's supported Markdown subset to HTML for sanitization.
 *
 * @param markdown - README Markdown text.
 * @returns HTML containing only the supported Markdown structure.
 */
export function renderMarkdownContent(markdown) {
    const state = {
        chunks: [],
        inCodeBlock: false,
        listType: null,
        paragraph: [],
    };
    String(markdown || "")
        .replace(/\r\n/g, "\n")
        .split("\n")
        .forEach((line) => renderMarkdownLine(line, state));
    flushParagraph(state);
    closeList(state);
    if (state.inCodeBlock) {
        state.chunks.push("</code></pre>");
    }
    return `<article class="utility-modal__markdown">${state.chunks.join("")}</article>`;
}
function renderMarkdownLine(line, state) {
    if (line.startsWith("```")) {
        renderCodeFence(state);
    }
    else if (state.inCodeBlock) {
        state.chunks.push(`${escapeHtml(line)}\n`);
    }
    else if (!line.trim()) {
        flushParagraph(state);
        closeList(state);
    }
    else if (isHeading(line)) {
        renderHeading(line, state);
    }
    else if (isUnorderedItem(line)) {
        renderListItem(line.match(/^\s*[-*]\s+(.+)$/)?.[1] || "", "ul", state);
    }
    else if (isOrderedItem(line)) {
        renderListItem(line.match(/^\s*\d+[.)]\s+(.+)$/)?.[1] || "", "ol", state);
    }
    else {
        closeList(state);
        state.paragraph.push(line.trim());
    }
}
function renderCodeFence(state) {
    flushParagraph(state);
    closeList(state);
    state.chunks.push(state.inCodeBlock ? "</code></pre>" : "<pre><code>");
    state.inCodeBlock = !state.inCodeBlock;
}
function isHeading(line) {
    return /^#{1,6}\s+(.+)$/.test(line);
}
function renderHeading(line, state) {
    flushParagraph(state);
    closeList(state);
    const match = line.match(/^(#{1,6})\s+(.+)$/);
    if (!match)
        return;
    const level = Math.min(match[1].length, 6);
    const content = renderMarkdownInline(match[2].trim());
    state.chunks.push(`<h${level}>${content}</h${level}>`);
}
function isUnorderedItem(line) {
    return /^\s*[-*]\s+(.+)$/.test(line);
}
function isOrderedItem(line) {
    return /^\s*\d+[.)]\s+(.+)$/.test(line);
}
function renderListItem(content, type, state) {
    flushParagraph(state);
    if (state.listType !== type) {
        closeList(state);
        state.chunks.push(`<${type}>`);
        state.listType = type;
    }
    state.chunks.push(`<li>${renderMarkdownInline(content.trim())}</li>`);
}
function flushParagraph(state) {
    if (state.paragraph.length === 0)
        return;
    const text = state.paragraph.join(" ").trim();
    state.paragraph = [];
    if (text)
        state.chunks.push(`<p>${renderMarkdownInline(text)}</p>`);
}
function closeList(state) {
    if (!state.listType)
        return;
    state.chunks.push(`</${state.listType}>`);
    state.listType = null;
}
function renderMarkdownInline(text) {
    return escapeHtml(text)
        .replace(/`([^`]+)`/g, "<code>$1</code>")
        .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
        .replace(/\*([^*]+)\*/g, "<em>$1</em>")
        .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, (_match, label, url) => {
        return `<a href="${url}" target="_blank" rel="noopener noreferrer">${label}</a>`;
    });
}
function escapeHtml(value) {
    return value
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}
