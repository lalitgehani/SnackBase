/**
 * Studio sidebar routes hidden in platform mode (customer instances).
 * Superadmin-only entries remain visible in self-host mode.
 */
export const PLATFORM_HIDDEN_STUDIO_ROUTES = ['/admin/accounts'] as const;

export type PlatformHiddenStudioRoute = (typeof PLATFORM_HIDDEN_STUDIO_ROUTES)[number];

export function isPlatformHiddenStudioRoute(adminPath: string): boolean {
  return (PLATFORM_HIDDEN_STUDIO_ROUTES as readonly string[]).includes(adminPath);
}

export function filterStudioNavItems<T extends { url: string }>(
  items: T[],
  platformMode: boolean,
): T[] {
  if (!platformMode) return items;
  return items.filter((item) => !isPlatformHiddenStudioRoute(item.url));
}
