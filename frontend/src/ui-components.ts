/** Reusable, framework-free behavior for Motion In Ocean UI primitives. */

export interface FilterableCollectionRow {
  dataset: { search?: string; status?: string };
  hidden: boolean;
  textContent: string | null;
}

export interface FeedbackElement {
  textContent: string | null;
  classList: { toggle(className: string, force?: boolean): void };
}

/** Data displayed by the reusable settings confirmation item. */
export interface SettingsConfirmationChange {
  category: string;
  property: string;
  oldValue: unknown;
  newValue: unknown;
}

/** Data displayed by the reusable runtime override summary item. */
export interface SettingsOverrideSummaryItem {
  category: string;
  key: string;
  value: unknown;
  envValue: unknown;
  restartable: boolean;
}

/**
 * Create a text-only element with the project's shared DOM construction behavior.
 *
 * @param document - Document used to create the element.
 * @param tagName - Supported semantic element tag.
 * @param className - CSS class applied to the element.
 * @param text - Literal text content; markup is never parsed.
 * @returns The created element with its class and text content set.
 */
export function createTextElement(
  document: Pick<Document, "createElement">,
  tagName: "div" | "li" | "span",
  className: string,
  text: string,
): HTMLElement {
  const element = document.createElement(tagName);
  element.className = className;
  element.textContent = text;
  return element;
}

/**
 * Build the reusable settings confirmation row from text-only child elements.
 *
 * @param document - Document used to create the elements.
 * @param change - Setting path and previous/new values to display.
 * @param formatValue - Formats a setting value for human-readable display.
 * @returns A list item for the settings confirmation dialog.
 */
export function createSettingsConfirmationChangeItem(
  document: Pick<Document, "createElement">,
  change: SettingsConfirmationChange,
  formatValue: (value: unknown) => string,
): HTMLLIElement {
  const item = document.createElement("li");
  item.className = "settings-confirm-change-item";
  item.replaceChildren(
    createTextElement(
      document,
      "span",
      "settings-confirm-change-path",
      `${change.category}.${change.property}`,
    ),
    createTextElement(
      document,
      "span",
      "settings-confirm-change-values",
      `${formatValue(change.oldValue)} → ${formatValue(change.newValue)}`,
    ),
  );
  return item;
}

/**
 * Build a reusable summary row for a setting overridden at runtime.
 *
 * @param document - Document used to create the elements.
 * @param item - Overridden setting and values to display.
 * @returns A summary row built with text-only DOM nodes.
 */
export function createSettingsOverrideSummaryItem(
  document: Pick<Document, "createElement">,
  item: SettingsOverrideSummaryItem,
): HTMLDivElement {
  const row = document.createElement("div");
  row.className = "settings-change-item";

  const path = createTextElement(
    document,
    "div",
    "settings-change-path",
    `${item.category}.${item.key}`,
  );
  const values = document.createElement("div");
  values.className = "settings-change-values";
  const valueElements = [
    createTextElement(document, "span", "settings-change-value", `Current: ${String(item.value)}`),
    createTextElement(
      document,
      "span",
      "settings-change-value",
      `Default: ${String(item.envValue)}`,
    ),
  ];

  if (item.restartable) {
    valueElements.push(
      createTextElement(document, "span", "settings-change-badge", "Restart required"),
    );
  }

  values.replaceChildren(...valueElements);
  row.replaceChildren(path, values);
  return row;
}

/** Set reusable feedback copy and its semantic visual tone. */
export function setFeedbackMessage(
  element: FeedbackElement | null,
  message: string,
  tone: "error" | "success" | "neutral" = "neutral",
): void {
  if (!element) return;
  element.textContent = message;
  element.classList.toggle("ui-feedback--error", tone === "error");
  element.classList.toggle("ui-feedback--success", tone === "success");
}

/** Filter a collection of rows by their searchable text and status category. */
export function filterCollectionRows(
  rows: Iterable<FilterableCollectionRow>,
  query: string,
  status: string,
): number {
  const normalizedQuery = query.trim().toLocaleLowerCase();
  const normalizedStatus = status.trim().toLocaleLowerCase();
  let visibleCount = 0;

  for (const row of rows) {
    const searchableText = (row.dataset.search || row.textContent || "").toLocaleLowerCase();
    const matchesQuery = normalizedQuery === "" || searchableText.includes(normalizedQuery);
    const matchesStatus =
      normalizedStatus === "" ||
      normalizedStatus === "all" ||
      row.dataset.status?.toLocaleLowerCase() === normalizedStatus;
    row.hidden = !(matchesQuery && matchesStatus);
    if (!row.hidden) visibleCount += 1;
  }

  return visibleCount;
}

export interface ConfirmationDialogOptions {
  title: string;
  message: string;
  confirmLabel: string;
  cancelLabel?: string;
  fallbackFocus?: HTMLElement | null;
}

/**
 * Show a reusable native confirmation dialog and resolve true only on confirmation.
 *
 * Escape and Cancel resolve false. If the invoking control is removed while the
 * dialog is open, focus moves to the supplied connected fallback after closing.
 */
export function confirmInDialog(
  dialog: HTMLDialogElement | null,
  options: ConfirmationDialogOptions,
): Promise<boolean> {
  if (!dialog || dialog.open) return Promise.resolve(false);

  const title = dialog.querySelector<HTMLElement>("[data-confirm-title]");
  const message = dialog.querySelector<HTMLElement>("[data-confirm-message]");
  const cancelButton = dialog.querySelector<HTMLButtonElement>("[data-confirm-cancel]");
  const confirmButton = dialog.querySelector<HTMLButtonElement>("[data-confirm-accept]");
  if (!title || !message || !cancelButton || !confirmButton) return Promise.resolve(false);

  title.textContent = options.title;
  message.textContent = options.message;
  cancelButton.textContent = options.cancelLabel || "Cancel";
  confirmButton.textContent = options.confirmLabel;

  const invoker = dialog.ownerDocument.activeElement;
  return new Promise<boolean>((resolve) => {
    const onClose = (): void => {
      if (invoker && !invoker.isConnected && options.fallbackFocus?.isConnected) {
        options.fallbackFocus.focus();
      }
      resolve(dialog.returnValue === "confirm");
    };

    dialog.returnValue = "";
    dialog.addEventListener("close", onClose, { once: true });
    try {
      dialog.showModal();
    } catch {
      dialog.removeEventListener("close", onClose);
      resolve(false);
    }
  });
}
