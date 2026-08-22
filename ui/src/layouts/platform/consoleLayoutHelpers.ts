/** Map pathname to console page title for the header. */
export function getConsolePageTitle(pathname: string): string {
  if (pathname.startsWith('/account')) return 'Account'
  if (pathname.includes('/projects/new')) return 'Create project'
  if (pathname.includes('/environments')) return 'Environments'
  if (pathname.includes('/projects')) return 'Projects'
  if (pathname === '/organizations/new' || pathname.endsWith('/organizations/new')) {
    return 'Create organization'
  }
  if (pathname.startsWith('/organizations')) return 'Organizations'
  return 'SnackBase Cloud'
}
