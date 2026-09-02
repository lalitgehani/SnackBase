/**
 * Path helpers for admin layout (titles, full-bleed routes).
 * Kept separate from AdminLayout so the layout file only exports components
 * (react-refresh/only-export-components).
 */

/** Full-bleed routes under /admin/workflows (not the list). */
export function isWorkflowEditorPath(pathname: string): boolean {
    if (!pathname.startsWith('/admin/workflows/')) return false;
    return pathname !== '/admin/workflows';
}

/** Full-bleed routes under /admin/hooks (not the list). */
export function isHookFullBleedPath(pathname: string): boolean {
    if (!pathname.startsWith('/admin/hooks/')) return false;
    return pathname !== '/admin/hooks';
}

export function isFullBleedAdminPath(pathname: string): boolean {
    return (
        pathname.startsWith('/admin/collections') ||
        isWorkflowEditorPath(pathname) ||
        isHookFullBleedPath(pathname)
    );
}

export function getAdminPageTitle(pathname: string): string {
    if (pathname === '/admin/dashboard') return 'Dashboard';
    if (pathname.startsWith('/admin/collections')) return 'Collections';
    if (pathname.startsWith('/admin/macros')) return 'Macros';
    if (pathname.startsWith('/admin/accounts')) return 'Accounts';
    if (pathname.startsWith('/admin/users')) return 'Users';
    if (pathname.startsWith('/admin/groups')) return 'Groups';
    if (pathname.startsWith('/admin/roles')) return 'Roles';
    if (pathname.startsWith('/admin/invitations')) return 'Invitations';
    if (pathname.startsWith('/admin/api-keys')) return 'API Keys';
    if (pathname === '/admin/hooks/new') return 'New Hook';
    if (pathname.match(/^\/admin\/hooks\/[^/]+\/edit$/)) return 'Edit Hook';
    if (pathname.match(/^\/admin\/hooks\/[^/]+$/)) return 'Hook Overview';
    if (pathname.startsWith('/admin/hooks')) return 'Hooks';
    if (pathname.startsWith('/admin/scheduled-tasks')) return 'Scheduled Tasks';
    if (pathname === '/admin/workflows/new') return 'New Workflow';
    if (pathname.match(/^\/admin\/workflows\/[^/]+\/edit$/)) return 'Edit Workflow';
    if (pathname.match(/^\/admin\/workflows\/[^/]+\/runs\/[^/]+$/)) return 'Workflow Run';
    if (pathname.match(/^\/admin\/workflows\/[^/]+$/)) return 'Workflow Overview';
    if (pathname.startsWith('/admin/workflows')) return 'Workflows';
    if (pathname.startsWith('/admin/jobs')) return 'Jobs';
    if (pathname.startsWith('/admin/backups/settings')) return 'Backup Settings';
    if (pathname.startsWith('/admin/backups')) return 'Backups';
    if (pathname.startsWith('/admin/webhooks')) return 'Webhooks';
    if (pathname.startsWith('/admin/endpoints')) return 'Endpoints';
    if (pathname.startsWith('/admin/configuration')) return 'Configuration';
    if (pathname.startsWith('/admin/audit-logs')) return 'Audit Logs';
    if (pathname.startsWith('/admin/migrations')) return 'Migrations';
    return 'Admin';
}
