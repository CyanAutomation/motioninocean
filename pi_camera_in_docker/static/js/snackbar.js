const SNACKBAR_DURATION_MS = 5000;
const browserClock = {
    setTimeout: (callback, delay) => window.setTimeout(callback, delay),
    clearTimeout: (handle) => window.clearTimeout(handle),
};
/**
 * Build a single-message snackbar controller for a page's live status region.
 *
 * Messages replace one another, disappear after five seconds, and stay visible while
 * the user is interacting with the region. Focus is never moved into the snackbar.
 */
export function createSnackbarController(region, clock = browserClock) {
    const message = region.querySelector("[data-snackbar-message]");
    const dismissButton = region.querySelector("[data-snackbar-dismiss]");
    let timeoutId = null;
    let pointerOver = false;
    let focusWithin = false;
    const stopTimer = () => {
        if (timeoutId !== null) {
            clock.clearTimeout(timeoutId);
            timeoutId = null;
        }
    };
    const dismiss = () => {
        stopTimer();
        pointerOver = false;
        focusWithin = false;
        region.classList.remove("snackbar--visible");
    };
    const startTimer = () => {
        stopTimer();
        if (!pointerOver && !focusWithin && region.classList.contains("snackbar--visible")) {
            timeoutId = clock.setTimeout(dismiss, SNACKBAR_DURATION_MS);
        }
    };
    const syncTimer = () => {
        if (pointerOver || focusWithin) {
            stopTimer();
        }
        else {
            startTimer();
        }
    };
    region.addEventListener("pointerenter", () => {
        pointerOver = true;
        syncTimer();
    });
    region.addEventListener("pointerleave", () => {
        pointerOver = false;
        syncTimer();
    });
    region.addEventListener("focusin", () => {
        focusWithin = true;
        syncTimer();
    });
    region.addEventListener("focusout", (event) => {
        if (!event.relatedTarget || !region.contains(event.relatedTarget)) {
            focusWithin = false;
            syncTimer();
        }
    });
    dismissButton?.addEventListener("click", dismiss);
    return {
        show(text) {
            if (!message || !text.trim())
                return;
            message.textContent = text;
            region.classList.add("snackbar--visible");
            startTimer();
        },
        dismiss,
    };
}
let sharedController = null;
/** Return the page-wide snackbar controller shared by independently loaded modules. */
export function getSnackbarController() {
    if (sharedController)
        return sharedController;
    const region = document.getElementById("app-snackbar");
    if (!region)
        return null;
    sharedController = createSnackbarController(region);
    return sharedController;
}
