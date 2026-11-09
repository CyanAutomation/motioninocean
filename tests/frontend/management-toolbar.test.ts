import test from "node:test";
import assert from "node:assert/strict";
import { bindDashboardControls } from "../../frontend/src/management-bootstrap.ts";
import { asTestDouble } from "./test-doubles.ts";

class MockControl {
  value = "";
  listeners = new Map<string, Array<(event: Event) => void>>();

  addEventListener(type: string, listener: Parameters<HTMLElement["addEventListener"]>[1]): void {
    const callback =
      typeof listener === "function" ? listener : (event: Event) => listener.handleEvent(event);
    const listeners = this.listeners.get(type) || [];
    listeners.push(callback);
    this.listeners.set(type, listeners);
  }

  emit(type: string): void {
    this.listeners.get(type)?.forEach((listener) => listener(new Event(type)));
  }
}

test("webcam toolbar applies filters after search and status changes", () => {
  const search = new MockControl();
  const status = new MockControl();
  let filterCalls = 0;
  const control = () => new MockControl();

  bindDashboardControls(
    asTestDouble<Parameters<typeof bindDashboardControls>[0]>({
      elements: {
        webcamForm: control(),
        cancelEditBtn: control(),
        refreshBtn: control(),
        tableBody: control(),
        webcamTransport: control(),
        webcamSearchInput: search,
        webcamStatusFilter: status,
      },
      actions: {
        submitNodeForm: () => {},
        resetForm: () => {},
        showFeedback: () => {},
        stopStatusRefreshInterval: () => {},
        refreshManagementData: async () => {},
        startStatusRefreshInterval: () => {},
        renderOverviewPanel: () => {},
        renderDiscoveredPanel: () => {},
        setDiscoveredFeedback: () => {},
        selectDiscoveredNode: () => {},
        applyDiscoveredDecision: async () => {},
        fetchOverview: async () => {},
        applyWebcamFilters: () => {
          filterCalls += 1;
        },
        saveSettings: () => {},
        resetSettings: () => {},
        fetchSettingsData: () => {},
        setNodeFormPanelCollapsed: () => {},
        getStoredNodeFormCollapsedPreference: () => true,
        toggleNodeFormPanel: () => {},
        onTableClick: () => {},
        updateBaseUrlValidation: () => {},
        setDiagnosticPanelExpanded: () => {},
        toggleDiagnosticPanelContent: () => {},
        getLatestDiagnosticResult: () => null,
        buildDiagnosticTextReport: () => "",
      },
    }),
  );

  search.emit("input");
  status.emit("change");
  assert.equal(filterCalls, 2);
});
