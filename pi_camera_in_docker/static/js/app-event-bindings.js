/** Attach event handlers only when their optional DOM targets exist. */
export function bindOptionalEventListeners(bindings) {
    for (const { target, type, listener } of bindings) {
        target?.addEventListener(type, listener);
    }
}
