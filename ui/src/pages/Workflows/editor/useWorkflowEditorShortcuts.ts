/**
 * Keyboard shortcuts for the workflow editor with focus guards.
 */

import { useEffect } from 'react';

/** True when the event target is an editable field (shortcuts should not fire). */
export function isEditableKeyboardTarget(target: EventTarget | null): boolean {
    if (!target || !(target instanceof Element)) return false;
    const el = target as HTMLElement;
    const tag = el.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
    // isContentEditable is unreliable in jsdom; check IDL property + attribute
    const ce = el.contentEditable;
    if (el.isContentEditable || ce === 'true' || el.getAttribute('contenteditable') === 'true') {
        return true;
    }
    // Radix / shadcn may use role=textbox
    if (el.closest('[contenteditable="true"]')) return true;
    if (el.closest('input, textarea, select, [role="textbox"]')) return true;
    return false;
}

export interface WorkflowShortcutHandlers {
    onSave?: () => void;
    onDeleteSelection?: () => void;
    onEscape?: () => void;
    /** When false, listeners are not attached. Default true. */
    enabled?: boolean;
}

/**
 * Attach window-level shortcut listeners for the editor.
 * Delete/Backspace are handled here so properties-panel typing never deletes nodes
 * (React Flow deleteKeyCode should be null when this is used).
 */
export function useWorkflowEditorShortcuts({
    onSave,
    onDeleteSelection,
    onEscape,
    enabled = true,
}: WorkflowShortcutHandlers): void {
    useEffect(() => {
        if (!enabled) return;

        const handler = (e: KeyboardEvent) => {
            if (isEditableKeyboardTarget(e.target)) {
                // Still allow Escape to blur-driven deselect? No — ignore all while typing.
                return;
            }

            const mod = e.metaKey || e.ctrlKey;

            if (mod && (e.key === 's' || e.key === 'S')) {
                e.preventDefault();
                onSave?.();
                return;
            }

            if (e.key === 'Escape') {
                onEscape?.();
                return;
            }

            if (e.key === 'Delete' || e.key === 'Backspace') {
                // Don't preventDefault on Backspace always — only when we handle delete
                if (onDeleteSelection) {
                    e.preventDefault();
                    onDeleteSelection();
                }
            }
        };

        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, [enabled, onSave, onDeleteSelection, onEscape]);
}
