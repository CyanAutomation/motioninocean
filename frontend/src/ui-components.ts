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

/** Resolve an explicit theme preference, falling back to the operating system. */
export function resolveThemePreference(
  storedPreference: string | null | undefined,
  prefersDark: boolean,
): "light" | "dark" {
  const normalizedPreference = storedPreference?.trim().toLocaleLowerCase();
  if (normalizedPreference === "light" || normalizedPreference === "dark") {
    return normalizedPreference;
  }
  return prefersDark ? "dark" : "light";
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
