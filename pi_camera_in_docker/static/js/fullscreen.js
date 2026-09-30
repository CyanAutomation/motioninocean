function isFullscreen(document) {
    return Boolean(document.fullscreenElement ||
        document.webkitFullscreenElement ||
        document.mozFullScreenElement ||
        document.msFullscreenElement);
}
/** Enter or leave fullscreen using native or browser-prefixed APIs. */
export async function toggleFullscreen(container, fullscreenDocument, logger = console) {
    if (!container)
        return;
    try {
        if (!isFullscreen(fullscreenDocument)) {
            if (container.requestFullscreen) {
                await container.requestFullscreen();
            }
            else if (container.webkitRequestFullscreen) {
                await container.webkitRequestFullscreen();
            }
            else if (container.mozRequestFullScreen) {
                await container.mozRequestFullScreen();
            }
            else if (container.msRequestFullscreen) {
                await container.msRequestFullscreen();
            }
            else {
                logger.warn("Fullscreen API is not supported in this browser");
            }
            return;
        }
        if (fullscreenDocument.exitFullscreen) {
            await fullscreenDocument.exitFullscreen();
        }
        else if (fullscreenDocument.webkitExitFullscreen) {
            await fullscreenDocument.webkitExitFullscreen();
        }
        else if (fullscreenDocument.mozCancelFullScreen) {
            await fullscreenDocument.mozCancelFullScreen();
        }
        else if (fullscreenDocument.msExitFullscreen) {
            await fullscreenDocument.msExitFullscreen();
        }
    }
    catch (error) {
        logger.error("Failed to toggle fullscreen:", error);
    }
}
