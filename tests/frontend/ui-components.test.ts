import test from "node:test";
import assert from "node:assert/strict";
import {
  confirmInDialog,
  filterCollectionRows,
  resolveThemePreference,
  setFeedbackMessage,
} from "../../frontend/src/ui-components.ts";

interface FilterRow {
  dataset: { search?: string; status?: string };
  hidden: boolean;
  textContent: string;
}

function makeRow(search: string, status: string): FilterRow {
  return { dataset: { search, status }, hidden: false, textContent: search };
}

class FakeConfirmationDialog extends EventTarget {
  open = false;
  returnValue = "";
  readonly title = { textContent: "" };
  readonly message = { textContent: "" };
  readonly cancelButton = { textContent: "" };
  readonly confirmButton = { textContent: "" };
  readonly ownerDocument = { activeElement: null as HTMLElement | null };

  querySelector(selector: string): Element | null {
    const targets: Record<string, Element> = {
      "[data-confirm-title]": this.title as unknown as Element,
      "[data-confirm-message]": this.message as unknown as Element,
      "[data-confirm-cancel]": this.cancelButton as unknown as Element,
      "[data-confirm-accept]": this.confirmButton as unknown as Element,
    };
    return targets[selector] || null;
  }

  showModal(): void {
    this.open = true;
  }

  close(returnValue = ""): void {
    this.open = false;
    this.returnValue = returnValue;
    this.dispatchEvent(new Event("close"));
  }
}

test("collection filters match searchable text and status independently", () => {
  const rows = [
    makeRow("North entrance cam north-01", "online"),
    makeRow("Workshop camera shop-02", "needs-attention"),
    makeRow("Garage cam garage-03", "online"),
  ];

  const count = filterCollectionRows(rows, "SHOP", "all");

  assert.equal(count, 1);
  assert.deepEqual(rows.map((row) => row.hidden), [true, false, true]);
});

test("collection filters combine the query with a selected status and support clearing", () => {
  const rows = [
    makeRow("North entrance cam north-01", "online"),
    makeRow("North workshop cam shop-02", "needs-attention"),
    makeRow("Garage cam garage-03", "online"),
  ];

  assert.equal(filterCollectionRows(rows, "north", "online"), 1);
  assert.deepEqual(rows.map((row) => row.hidden), [false, true, true]);
  assert.equal(filterCollectionRows(rows, "", "all"), 3);
  assert.deepEqual(rows.map((row) => row.hidden), [false, false, false]);
});

test("theme preference respects an explicit selection and otherwise follows the system", () => {
  assert.equal(resolveThemePreference("dark", false), "dark");
  assert.equal(resolveThemePreference("light", true), "light");
  assert.equal(resolveThemePreference(null, true), "dark");
  assert.equal(resolveThemePreference("invalid", false), "light");
});

test("feedback component clears old tone classes when the message changes", () => {
  const classes = new Set<string>();
  const feedback = {
    textContent: "",
    classList: {
      toggle(className: string, force?: boolean) {
        if (force) classes.add(className);
        else classes.delete(className);
      },
    },
  };

  setFeedbackMessage(feedback, "Could not connect.", "error");
  assert.equal(feedback.textContent, "Could not connect.");
  assert.equal(classes.has("ui-feedback--error"), true);
  assert.equal(classes.has("ui-feedback--success"), false);

  setFeedbackMessage(feedback, "Saved.", "success");
  assert.equal(feedback.textContent, "Saved.");
  assert.equal(classes.has("ui-feedback--error"), false);
  assert.equal(classes.has("ui-feedback--success"), true);
});

test("confirmation dialog updates reusable copy and resolves only an explicit confirm", async () => {
  const dialog = new FakeConfirmationDialog();
  const confirmation = confirmInDialog(dialog as unknown as HTMLDialogElement, {
    title: "Delete webcam?",
    message: "This removes north-01 from the hub.",
    confirmLabel: "Delete webcam",
  });

  assert.equal(dialog.open, true);
  assert.equal(dialog.title.textContent, "Delete webcam?");
  assert.equal(dialog.message.textContent, "This removes north-01 from the hub.");
  assert.equal(dialog.confirmButton.textContent, "Delete webcam");

  dialog.close("cancel");
  assert.equal(await confirmation, false);

  const confirmed = confirmInDialog(dialog as unknown as HTMLDialogElement, {
    title: "Reset settings?",
    message: "Saved settings will return to their defaults.",
    confirmLabel: "Reset settings",
  });
  dialog.close("confirm");
  assert.equal(await confirmed, true);
});

test("confirmation dialog fails closed when unavailable or already open", async () => {
  assert.equal(
    await confirmInDialog(null, {
      title: "Delete webcam?",
      message: "This cannot be undone.",
      confirmLabel: "Delete webcam",
    }),
    false,
  );

  const dialog = new FakeConfirmationDialog();
  dialog.open = true;
  assert.equal(
    await confirmInDialog(dialog as unknown as HTMLDialogElement, {
      title: "Delete webcam?",
      message: "This cannot be undone.",
      confirmLabel: "Delete webcam",
    }),
    false,
  );
});

test("confirmation dialog restores focus if its invoking control is removed", async () => {
  const dialog = new FakeConfirmationDialog();
  let fallbackFocused = false;
  dialog.ownerDocument.activeElement = { isConnected: false } as HTMLElement;

  const confirmation = confirmInDialog(dialog as unknown as HTMLDialogElement, {
    title: "Remove webcam?",
    message: "The webcam will be removed from this hub.",
    confirmLabel: "Remove webcam",
    fallbackFocus: {
      isConnected: true,
      focus: () => {
        fallbackFocused = true;
      },
    } as unknown as HTMLElement,
  });
  dialog.close("cancel");

  assert.equal(await confirmation, false);
  assert.equal(fallbackFocused, true);
});

test("confirmation dialog fails closed when the browser cannot open it", async () => {
  const dialog = new FakeConfirmationDialog();
  dialog.showModal = () => {
    throw new Error("Dialog API unavailable");
  };

  assert.equal(
    await confirmInDialog(dialog as unknown as HTMLDialogElement, {
      title: "Remove webcam?",
      message: "The webcam will be removed from this hub.",
      confirmLabel: "Remove webcam",
    }),
    false,
  );
});
