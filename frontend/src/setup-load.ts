export interface SetupLoadDependencies {
  panelAvailable: boolean;
  fetchTemplates: () => Promise<unknown>;
  setLoading: (isLoading: boolean) => void;
  applyTemplates: (data: unknown) => void;
  isInitialized: () => boolean;
  initializeEventListeners: () => void;
  setWizardStep: () => void;
  setStatus: (status: "ready" | "error") => void;
  onError: (error: unknown) => void;
  logger: {
    error: (message: string, error: unknown) => void;
  };
}

/** Fetch setup templates and coordinate the wizard's loading and ready states. */
export async function loadSetupTemplates(dependencies: SetupLoadDependencies): Promise<void> {
  if (!dependencies.panelAvailable) return;

  try {
    dependencies.setLoading(true);
    const data = await dependencies.fetchTemplates();
    dependencies.applyTemplates(data);
    if (!dependencies.isInitialized()) {
      dependencies.initializeEventListeners();
    }
    dependencies.setWizardStep();
    dependencies.setStatus("ready");
  } catch (error) {
    dependencies.logger.error("Failed to load setup tab:", error);
    dependencies.onError(error);
    dependencies.setStatus("error");
  } finally {
    dependencies.setLoading(false);
  }
}
