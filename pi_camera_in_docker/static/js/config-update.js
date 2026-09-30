function isAbortError(error) {
    return (typeof error === "object" && error !== null && "name" in error && error.name === "AbortError");
}
function errorMessage(error) {
    return typeof error === "object" &&
        error !== null &&
        "message" in error &&
        typeof error.message === "string" &&
        error.message.length > 0
        ? error.message
        : "Unknown error";
}
/** Fetch, display, and clean up one config refresh cycle. */
export async function runConfigUpdate(state, dependencies) {
    if (state.configInFlight || !dependencies.isActive)
        return;
    const showHeavyLoading = state.configInitialLoadPending;
    const schedule = dependencies.schedule || setTimeout;
    const cancel = dependencies.cancel || clearTimeout;
    try {
        state.configInFlight = true;
        if (showHeavyLoading && dependencies.loadingElement) {
            state.configLoadingDelayTimer = schedule(() => {
                state.configLoadingVisible = true;
                dependencies.loadingElement?.classList.remove("hidden");
            }, 400);
        }
        try {
            const data = await dependencies.fetchConfig();
            dependencies.renderConfig(data);
            state.lastConfigUpdate = new Date();
            dependencies.onSuccess?.();
        }
        catch (error) {
            if (isAbortError(error)) {
                dependencies.logger.warn("Config request timed out, will retry.");
                dependencies.showConfigError("Configuration request timed out. Will retry automatically.");
                return;
            }
            dependencies.logger.error("Failed to fetch config:", error);
            dependencies.clearConfigDisplay();
            dependencies.showConfigError(`Failed to load configuration: ${errorMessage(error)}`);
        }
    }
    finally {
        state.configInFlight = false;
        state.configInitialLoadPending = false;
        if (state.configLoadingDelayTimer) {
            cancel(state.configLoadingDelayTimer);
            state.configLoadingDelayTimer = null;
        }
        if (state.configLoadingVisible && dependencies.loadingElement) {
            dependencies.loadingElement.classList.add("hidden");
            state.configLoadingVisible = false;
        }
    }
}
