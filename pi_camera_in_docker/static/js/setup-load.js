/** Fetch setup templates and coordinate the wizard's loading and ready states. */
export async function loadSetupTemplates(dependencies) {
    if (!dependencies.panelAvailable)
        return;
    try {
        dependencies.setLoading(true);
        const data = await dependencies.fetchTemplates();
        dependencies.applyTemplates(data);
        if (!dependencies.isInitialized()) {
            dependencies.initializeEventListeners();
        }
        dependencies.setWizardStep();
        dependencies.setStatus("ready");
    }
    catch (error) {
        dependencies.logger.error("Failed to load setup tab:", error);
        dependencies.onError(error);
        dependencies.setStatus("error");
    }
    finally {
        dependencies.setLoading(false);
    }
}
