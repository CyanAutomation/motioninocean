/** Retry an MJPEG stream after disconnects and pause it while the page is hidden. */

export const STREAM_RECONNECT_BASE_DELAY_MS = 1000;
export const STREAM_RECONNECT_MAX_DELAY_MS = 30_000;

export type StreamReconnectTimer = ReturnType<typeof setTimeout> | number;

export interface StreamReconnectImage {
  setAttribute(name: string, value: string): void;
  removeAttribute(name: string): void;
}

export interface StreamReconnectDependencies {
  currentHref: string;
  isVisible: () => boolean;
  now: () => number;
  schedule: (callback: () => void, delayMs: number) => StreamReconnectTimer;
  cancel: (timer: StreamReconnectTimer) => void;
}

export interface StreamReconnectController {
  onError(): void;
  onLoad(): void;
  onVisibilityChange(): void;
  refresh(): void;
  dispose(): void;
}

/** Return true when the browser already decoded a frame before listeners attached. */
export function imageHasLoadedFrame(image: Pick<HTMLImageElement, "complete" | "naturalWidth">): boolean {
  return image.complete && image.naturalWidth > 0;
}

/**
 * Create a reconnect controller for a live MJPEG image.
 *
 * Requests are retried with capped exponential backoff. Hidden pages close the
 * stream request so an abandoned background tab does not keep a Cloud Run
 * instance busy; becoming visible starts a fresh stream request.
 *
 * @param image - Image element that owns the MJPEG request.
 * @param streamUrl - Relative or absolute URL for the MJPEG endpoint.
 * @param dependencies - Clock and visibility dependencies, overridable in tests.
 * @returns Controller methods for image events, page visibility, refresh, and cleanup.
 */
export function createStreamReconnectController(
  image: StreamReconnectImage,
  streamUrl: string,
  dependencies: Partial<StreamReconnectDependencies> = {},
): StreamReconnectController {
  const currentHref =
    dependencies.currentHref ??
    (typeof window === "undefined" ? "http://localhost/" : window.location.href);
  const isVisible = dependencies.isVisible ?? (() => typeof document === "undefined" || !document.hidden);
  const now = dependencies.now ?? Date.now;
  const schedule = dependencies.schedule ?? ((callback, delayMs) => setTimeout(callback, delayMs));
  const cancel = dependencies.cancel ?? ((timer) => clearTimeout(timer));
  let retryAttempt = 0;
  let requestSequence = 0;
  let retryTimer: StreamReconnectTimer | null = null;
  let paused = !isVisible();
  let disposed = false;

  function clearRetryTimer(): void {
    if (retryTimer === null) return;
    cancel(retryTimer);
    retryTimer = null;
  }

  function startStream(): void {
    if (disposed || paused || !isVisible()) return;
    requestSequence += 1;
    const url = new URL(streamUrl, currentHref);
    url.searchParams.set("_stream_retry", `${now()}-${requestSequence}`);
    image.setAttribute("src", url.href);
  }

  function onError(): void {
    if (disposed || paused || !isVisible()) return;
    clearRetryTimer();
    const delay = Math.min(
      STREAM_RECONNECT_BASE_DELAY_MS * 2 ** retryAttempt,
      STREAM_RECONNECT_MAX_DELAY_MS,
    );
    retryAttempt = Math.min(retryAttempt + 1, 8);
    retryTimer = schedule(() => {
      retryTimer = null;
      startStream();
    }, delay);
  }

  function onLoad(): void {
    retryAttempt = 0;
    clearRetryTimer();
  }

  function refresh(): void {
    retryAttempt = 0;
    clearRetryTimer();
    if (!isVisible()) {
      paused = true;
      image.removeAttribute("src");
      return;
    }
    paused = false;
    startStream();
  }

  function onVisibilityChange(): void {
    if (!isVisible()) {
      paused = true;
      clearRetryTimer();
      image.removeAttribute("src");
      return;
    }
    if (!paused) return;
    paused = false;
    retryAttempt = 0;
    startStream();
  }

  function dispose(): void {
    disposed = true;
    paused = true;
    clearRetryTimer();
    image.removeAttribute("src");
  }

  if (paused) image.removeAttribute("src");

  return { onError, onLoad, onVisibilityChange, refresh, dispose };
}
