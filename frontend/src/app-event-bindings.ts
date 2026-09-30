export interface OptionalEventBinding {
  target: EventTarget | null | undefined;
  type: string;
  listener: Parameters<EventTarget["addEventListener"]>[1];
}

/** Attach event handlers only when their optional DOM targets exist. */
export function bindOptionalEventListeners(bindings: OptionalEventBinding[]): void {
  for (const { target, type, listener } of bindings) {
    target?.addEventListener(type, listener);
  }
}
