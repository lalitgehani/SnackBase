/** Dispatch delete request from a card's hover control to the editor page. */
export function emitNodeDelete(nodeId: string) {
    window.dispatchEvent(
        new CustomEvent('workflow-node-delete', { detail: { nodeId } }),
    );
}
