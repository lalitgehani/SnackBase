/**
 * E2E route helper — resolves Studio paths for self-host vs platform mode (F4.7).
 */
export function studioPath(route: string, ref = 'production'): string {
  const normalized = route.startsWith('/') ? route : `/${route}`;
  const isPlatform = process.env.PLAYWRIGHT_PLATFORM === 'true';

  if (isPlatform) {
    const suffix = normalized.startsWith('/admin/')
      ? normalized.slice('/admin'.length)
      : normalized.startsWith('/admin')
        ? '/dashboard'
        : normalized;
    return `/project/${ref}${suffix}`;
  }

  if (normalized.startsWith('/admin')) {
    return normalized;
  }
  return `/admin${normalized}`;
}
