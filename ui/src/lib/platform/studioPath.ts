import { IS_PLATFORM } from '@/lib/config';

const ADMIN_PREFIX = '/admin';
const PROJECT_PREFIX = '/project';

/**
 * Resolve a Studio route for the active mode.
 * Self-host: `/admin/{route}` — Platform: `/project/{ref}/{route}`.
 */
export function studioPath(route: string, ref?: string): string {
  const normalized = route.startsWith('/') ? route : `/${route}`;

  if (IS_PLATFORM) {
    if (!ref) {
      throw new Error('studioPath requires ref in platform mode');
    }
    const suffix = normalized.startsWith(`${ADMIN_PREFIX}/`)
      ? normalized.slice(ADMIN_PREFIX.length)
      : normalized.startsWith(ADMIN_PREFIX)
        ? ''
        : normalized;
    return `${PROJECT_PREFIX}/${ref}${suffix || '/dashboard'}`;
  }

  if (normalized.startsWith(ADMIN_PREFIX)) {
    return normalized;
  }
  return `${ADMIN_PREFIX}${normalized}`;
}

/** Map `/project/:ref/...` back to `/admin/...` for shared layout helpers. */
export function normalizeToAdminPath(pathname: string): string {
  const match = pathname.match(/^\/project\/[^/]+(\/.*)?$/);
  if (match) {
    return `${ADMIN_PREFIX}${match[1] ?? ''}`;
  }
  return pathname;
}

/** Strip `/admin` prefix to a relative studio segment (e.g. `/collections`). */
export function adminSuffix(path: string): string {
  if (path.startsWith(`${ADMIN_PREFIX}/`)) {
    return path.slice(ADMIN_PREFIX.length);
  }
  if (path === ADMIN_PREFIX) {
    return '/dashboard';
  }
  return path.startsWith('/') ? path : `/${path}`;
}

export const LAST_PROJECT_REF_KEY = 'snackbase.platform.lastProjectRef';

export function rememberProjectRef(ref: string): void {
  if (typeof sessionStorage !== 'undefined') {
    sessionStorage.setItem(LAST_PROJECT_REF_KEY, ref);
  }
}

export function getLastProjectRef(): string | null {
  if (typeof sessionStorage === 'undefined') return null;
  return sessionStorage.getItem(LAST_PROJECT_REF_KEY);
}
