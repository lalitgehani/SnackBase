import { useEffect } from 'react';

const DEFAULT_MESSAGE =
  'You have unsaved function changes. Leave this page and discard them?';

/**
 * Guard against losing dirty Function editor state.
 *
 * - `beforeunload` covers browser reload / tab close.
 * - Capture-phase click handling confirms before internal `<a href>` navigations
 *   (Back to Functions, sidebar links, etc.).
 */
export function useUnsavedChangesGuard(when: boolean, message = DEFAULT_MESSAGE) {
  useEffect(() => {
    if (!when) return;
    const onBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = message;
    };
    window.addEventListener('beforeunload', onBeforeUnload);
    return () => window.removeEventListener('beforeunload', onBeforeUnload);
  }, [when, message]);

  useEffect(() => {
    if (!when) return;
    const onClick = (event: MouseEvent) => {
      if (event.defaultPrevented) return;
      if (event.button !== 0) return;
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const target = event.target as HTMLElement | null;
      const anchor = target?.closest?.('a[href]') as HTMLAnchorElement | null;
      if (!anchor) return;
      const href = anchor.getAttribute('href');
      if (!href || href.startsWith('#') || href.startsWith('mailto:')) return;
      if (/^https?:\/\//i.test(href)) return;
      // Same-page hash / current path — allow
      const current = `${window.location.pathname}${window.location.search}`;
      if (href === current || href === window.location.pathname) return;
      if (!window.confirm(message)) {
        event.preventDefault();
        event.stopPropagation();
      }
    };
    document.addEventListener('click', onClick, true);
    return () => document.removeEventListener('click', onClick, true);
  }, [when, message]);
}
