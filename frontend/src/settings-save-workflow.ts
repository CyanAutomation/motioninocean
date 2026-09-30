export interface SettingsSaveChange {
  category: string;
  property: string;
  oldValue: unknown;
  newValue: unknown;
}

export interface SettingsSaveResult<Settings> {
  kind: "saved" | "restart-required";
  settings: Settings;
  modifiedOnRestart?: unknown[] | null;
}

export interface SettingsSaveWorkflowDependencies<Settings, Patch> {
  isDirty: () => boolean;
  dirtyFieldCount: () => number;
  getPendingChanges: () => SettingsSaveChange[];
  confirm: (changes: SettingsSaveChange[]) => Promise<boolean>;
  buildPatch: (changes: SettingsSaveChange[], valueKey: "oldValue" | "newValue") => Patch;
  getSaveButton: () => { disabled: boolean } | null;
  save: (patch: Patch) => Promise<
    | SettingsSaveResult<Settings>
    | {
        kind: "validation-error";
        message: string;
      }
  >;
  setCurrentSettings: (settings: Settings) => void;
  clearDirtyFields: () => void;
  setUndoState: (snapshot: Patch, changes: SettingsSaveChange[]) => void;
  updateSaveButton: () => void;
  refreshChangesSummary: () => Promise<void>;
  showWarning: (message: string, metadata?: Record<string, string>) => void;
  showError: (message: string, metadata?: Record<string, string>) => void;
  showSuccess: (message: string, metadata?: Record<string, string>) => void;
  logError: (error: unknown) => void;
  describeError: (error: unknown) => string;
}

/** Coordinate settings validation, confirmation, persistence, and UI feedback. */
export async function runSettingsSaveWorkflow<Settings, Patch>(
  dependencies: SettingsSaveWorkflowDependencies<Settings, Patch>,
): Promise<void> {
  if (!dependencies.isDirty() || dependencies.dirtyFieldCount() === 0) {
    dependencies.showWarning("No changes to save");
    return;
  }

  const pendingChanges = dependencies.getPendingChanges();
  if (pendingChanges.length === 0) {
    dependencies.showWarning("No valid settings changes found");
    return;
  }

  if (!(await dependencies.confirm(pendingChanges))) return;

  const patch = dependencies.buildPatch(pendingChanges, "newValue");
  const snapshotPatch = dependencies.buildPatch(pendingChanges, "oldValue");
  const button = dependencies.getSaveButton();

  try {
    if (button) button.disabled = true;

    const result = await dependencies.save(patch);
    if (result.kind === "validation-error") {
      if (button) button.disabled = false;
      dependencies.showError("Validation error:\n" + result.message, {
        outcome: "failed",
        details: result.message,
      });
      return;
    }

    dependencies.setCurrentSettings(result.settings);
    dependencies.clearDirtyFields();
    dependencies.setUndoState(snapshotPatch, pendingChanges);
    dependencies.updateSaveButton();
    await dependencies.refreshChangesSummary();

    if (result.kind === "saved") {
      dependencies.showSuccess("Settings saved successfully!", { outcome: "saved" });
      return;
    }

    const restartDetails = result.modifiedOnRestart
      ? result.modifiedOnRestart.join("\n")
      : "Server restart required to apply some settings.";
    dependencies.showWarning(
      "Settings saved! Some changes require server restart:\n" + restartDetails,
      { outcome: "restart-required", details: restartDetails },
    );
  } catch (error) {
    dependencies.logError(error);
    const message = dependencies.describeError(error);
    dependencies.showError("Failed to save settings: " + message, {
      outcome: "failed",
      details: message,
    });
    if (button) button.disabled = false;
  }
}
