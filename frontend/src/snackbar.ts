const SNACKBAR_DURATION_MS = 5000;

interface SnackbarRegion extends HTMLElement {
  querySelector<T extends Element = Element>(selectors: string): T | null;
}

interface SnackbarClock {
  setTimeout(callback: () => void, delay: number): number;
  clearTimeout(handle: number): void;
}

const browserClock: SnackbarClock = {
  setTimeout: (callback, delay) => window.setTimeout(callback, delay),
  clearTimeout: (handle) => window.clearTimeout(handle),
};

/**
 * Build a single-message snackbar controller for a page's live status region.
 *
 * Messages replace one another, disappear after five seconds, and stay visible while
 * the user is interacting with the region. Focus is never moved into the snackbar.
 */
export function createSnackbarController(
  region: SnackbarRegion,
  clock: SnackbarClock = browserClock,
): { show: (message: string) => void; dismiss: () => void } {
  const message = region.querySelector<HTMLElement>("[data-snackbar-message]");
  const dismissButton = region.querySelector<HTMLButtonElement>("[data-snackbar-dismiss]");
  let timeoutId: number | null = null;
  let paused = false;

  const stopTimer = () => {
    if (timeoutId !== null) {
      clock.clearTimeout(timeoutId);
      timeoutId = null;
    }
  };

  const dismiss = () => {
    stopTimer();
    region.classList.remove("snackbar--visible");
  };

  const startTimer = () => {
    stopTimer();
    if (!paused && region.classList.contains("snackbar--visible")) {
      timeoutId = clock.setTimeout(dismiss, SNACKBAR_DURATION_MS);
    }
  };

  region.addEventListener("pointerenter", () => {
    paused = true;
    stopTimer();
  });
  region.addEventListener("pointerleave", () => {
    paused = false;
    startTimer();
  });
  region.addEventListener("focusin", () => {
    paused = true;
    stopTimer();
  });
  region.addEventListener("focusout", (event) => {
    if (!event.relatedTarget || !region.contains(event.relatedTarget as Node)) {
      paused = false;
      startTimer();
    }
  });
  dismissButton?.addEventListener("click", dismiss);

  return {
    show(text: string) {
      if (!message || !text.trim()) return;
      message.textContent = text;
      region.classList.add("snackbar--visible");
      startTimer();
    },
    dismiss,
  };
}

let sharedController: ReturnType<typeof createSnackbarController> | null = null;

/** Return the page-wide snackbar controller shared by independently loaded modules. */
export function getSnackbarController(): ReturnType<typeof createSnackbarController> | null {
  if (sharedController) return sharedController;
  const region = document.getElementById("app-snackbar");
  if (!region) return null;
  sharedController = createSnackbarController(region);
  return sharedController;
}
