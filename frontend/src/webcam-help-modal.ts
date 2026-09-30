export interface HelpContentPayload {
  content?: unknown;
  documentation_url?: unknown;
  message?: unknown;
}

export interface HelpModalPayload {
  title: string;
  htmlContent: string;
}

export interface WebcamHelpModalDependencies {
  fetchReadme: () => Promise<HelpContentPayload>;
  openModal: (payload: HelpModalPayload) => void;
  renderMarkdown: (markdown: string) => string;
  sanitizeHtml: (html: string) => string;
  escapeHtml: (value: unknown) => string;
  warn: (message: string, error: unknown) => void;
}

/** Load, render, and display README help content with safe fallback paths. */
export async function showWebcamHelpModal(
  dependencies: WebcamHelpModalDependencies,
): Promise<void> {
  dependencies.openModal({
    title: "Help",
    htmlContent: "<p>Loading help documentation…</p>",
  });

  try {
    const helpPayload = await dependencies.fetchReadme();
    const readmeContent = typeof helpPayload.content === "string" ? helpPayload.content.trim() : "";
    const documentationUrl =
      typeof helpPayload.documentation_url === "string" ? helpPayload.documentation_url.trim() : "";
    const helpMessage =
      typeof helpPayload.message === "string" && helpPayload.message.trim()
        ? helpPayload.message
        : "Help documentation is temporarily unavailable.";

    if (readmeContent) {
      let safeHelpHtml = "";
      try {
        const renderedMarkdownHtml = dependencies.renderMarkdown(helpPayload.content as string);
        safeHelpHtml = dependencies.sanitizeHtml(renderedMarkdownHtml);
      } catch (error) {
        dependencies.warn("Help markdown rendering failed; using plain-text fallback.", error);
        safeHelpHtml = `<pre>${dependencies.escapeHtml(readmeContent)}</pre>`;
      }

      dependencies.openModal({ title: "Help", htmlContent: safeHelpHtml });
      return;
    }

    if (documentationUrl) {
      dependencies.openModal({
        title: "Help",
        htmlContent: [
          `<p>${dependencies.escapeHtml(helpMessage)}</p>`,
          `<p><a href="${dependencies.escapeHtml(documentationUrl)}" target="_blank" rel="noopener noreferrer">Open documentation</a></p>`,
        ].join(""),
      });
      return;
    }

    dependencies.openModal({
      title: "Help",
      htmlContent: `<p>${dependencies.escapeHtml(helpMessage)}</p>`,
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    dependencies.openModal({
      title: "Help",
      htmlContent: `<p>${dependencies.escapeHtml(errorMessage || "Unable to load help documentation.")}</p>`,
    });
  }
}
