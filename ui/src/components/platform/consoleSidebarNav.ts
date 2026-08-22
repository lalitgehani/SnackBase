/** Prefix-match for simple nav URLs (exact or nested under the item). */
export function isNavActive(pathname: string, url: string): boolean {
  if (pathname === url) return true
  if (url !== '/' && pathname.startsWith(`${url}/`)) return true
  return false
}

/**
 * Organizations is only active on org list / create (and future org-level
 * routes). Nested project and environment paths live under
 * `/organizations/:id/projects…` and must highlight Projects instead.
 */
export function isOrganizationsNavActive(pathname: string): boolean {
  if (!pathname.startsWith('/organizations')) return false
  if (pathname.includes('/projects')) return false
  return true
}

/** Projects (and environments under a project) highlight the Projects item. */
export function isProjectsNavActive(pathname: string): boolean {
  return pathname.includes('/projects')
}
