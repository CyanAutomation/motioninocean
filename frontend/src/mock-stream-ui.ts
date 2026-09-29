export interface MockStreamElements {
  videoStream: HTMLElement | null;
  mockStreamPlaceholder: HTMLElement | null;
  mockStreamAnimation: HTMLElement | null;
  refreshBtn: HTMLElement | null;
  fullscreenBtn: HTMLElement | null;
}

export interface MockStreamContext {
  elements: MockStreamElements;
  document: Pick<Document, "getElementById">;
  setConnectionStatus: (status: string, message: string) => void;
}

/**
 * Update the stream placeholder, controls, and connection message for mock mode.
 *
 * @param isMockModeActive - Whether the mock camera placeholder should be visible.
 * @param isFallbackActive - Whether mock output is standing in for a failed camera.
 * @param context - DOM elements and status callback used by the webcam page.
 * @returns Nothing.
 */
export function applyMockStreamMode(
  isMockModeActive: boolean,
  isFallbackActive: boolean,
  context: MockStreamContext,
): void {
  const title = getStreamTitles(isMockModeActive);
  updatePlaceholder(context.elements, isMockModeActive);
  updateVideo(context.elements.videoStream, isMockModeActive);
  updateControlTitles(context, title.refresh, title.fullscreen);
  showMockConnectionStatus(context, isMockModeActive, isFallbackActive);
}

function getStreamTitles(isMockModeActive: boolean): { refresh: string; fullscreen: string } {
  return {
    refresh: isMockModeActive ? "Refresh stream (mock mode active)" : "Refresh stream",
    fullscreen: isMockModeActive ? "Toggle fullscreen (mock preview)" : "Toggle fullscreen",
  };
}

function updatePlaceholder(elements: MockStreamElements, isMockModeActive: boolean): void {
  if (elements.mockStreamPlaceholder) {
    elements.mockStreamPlaceholder.hidden = !isMockModeActive;
  }
  const animation = elements.mockStreamAnimation;
  if (!animation) return;
  animation.classList.toggle("mock-stream-animation--failed", false);
  if (isMockModeActive) restartEmbeddedAnimation(animation);
}

function restartEmbeddedAnimation(animation: HTMLElement): void {
  const source = animation.getAttribute("data");
  if (!source) return;
  animation.removeAttribute("data");
  animation.setAttribute("data", source);
}

function updateVideo(video: HTMLElement | null, isMockModeActive: boolean): void {
  if (!video) return;
  video.style.opacity = isMockModeActive ? "0.2" : "1";
  video.style.filter = isMockModeActive ? "grayscale(1)" : "none";
  video.setAttribute("aria-hidden", String(isMockModeActive));
}

function updateControlTitles(
  context: MockStreamContext,
  refreshTitle: string,
  fullscreenTitle: string,
): void {
  setTitle(context.elements.refreshBtn, refreshTitle);
  setTitle(context.elements.fullscreenBtn, fullscreenTitle);
  setTitle(context.document.getElementById("vc-refresh-btn"), refreshTitle);
  setTitle(context.document.getElementById("vc-fullscreen-btn"), fullscreenTitle);
}

function setTitle(element: HTMLElement | null, title: string): void {
  if (element) element.title = title;
}

function showMockConnectionStatus(
  context: MockStreamContext,
  isMockModeActive: boolean,
  isFallbackActive: boolean,
): void {
  if (!isMockModeActive) return;
  const message = isFallbackActive
    ? "Mock fallback active (camera unavailable)"
    : "Mock camera mode active";
  context.setConnectionStatus("inactive", message);
}
