/**
 * Keyboard shortcuts for the Collections workspace.
 * Only active when focus is not in an editable field.
 */

import { useEffect, useCallback } from 'react';

export const COLLECTION_BROWSER_SEARCH_ID = 'collection-browser-search';
export const SCHEMA_ADD_FIELD_TEST_ID = 'schema-add-field';
export const SHORTCUTS_HELP_TRIGGER_ID = 'collections-shortcuts-help';

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;

  const tag = target.tagName;
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
  if (target.isContentEditable) return true;

  const role = target.getAttribute('role');
  if (role === 'textbox' || role === 'combobox' || role === 'searchbox') {
    return true;
  }

  // Radix select / cmdk often focus nested elements
  if (target.closest('[contenteditable="true"]')) return true;
  if (target.closest('[role="textbox"]')) return true;
  if (target.closest('[role="combobox"]')) return true;

  return false;
}

export interface UseCollectionsWorkspaceShortcutsOptions {
  /** When false, listeners are not attached. Default true. */
  enabled?: boolean;
  /** Called when Shift+/ opens help (optional; button can also open). */
  onOpenHelp?: () => void;
}

/**
 * Register workspace shortcuts:
 * - `/` focus collection browser search
 * - `a` click Add Field when present
 * - `?` open shortcuts help
 */
export function useCollectionsWorkspaceShortcuts(
  options: UseCollectionsWorkspaceShortcutsOptions = {},
): void {
  const { enabled = true, onOpenHelp } = options;

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enabled) return;
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      if (isEditableTarget(event.target)) return;

      // Shift+/ produces '?' on most layouts
      if (event.key === '?' || (event.key === '/' && event.shiftKey)) {
        event.preventDefault();
        onOpenHelp?.();
        const trigger = document.getElementById(SHORTCUTS_HELP_TRIGGER_ID);
        trigger?.click();
        return;
      }

      if (event.key === '/') {
        event.preventDefault();
        const search = document.getElementById(
          COLLECTION_BROWSER_SEARCH_ID,
        ) as HTMLInputElement | null;
        search?.focus();
        search?.select();
        return;
      }

      if (event.key === 'a' || event.key === 'A') {
        const addBtn = document.querySelector<HTMLButtonElement>(
          `[data-testid="${SCHEMA_ADD_FIELD_TEST_ID}"]`,
        );
        if (addBtn && !addBtn.disabled) {
          event.preventDefault();
          addBtn.click();
        }
      }
    },
    [enabled, onOpenHelp],
  );

  useEffect(() => {
    if (!enabled) return;
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [enabled, handleKeyDown]);
}

/** Exported for unit tests */
export { isEditableTarget };
