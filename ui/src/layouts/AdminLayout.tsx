/**
 * Admin layout with sidebar navigation
 */

import { Outlet, useLocation } from 'react-router';
import { SidebarInset, SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar';
import { AppSidebar } from '@/components/AppSidebar';
import { ModeToggle } from '@/components/mode-toggle';

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
    if (pathname.startsWith('/admin/webhooks')) return 'Webhooks';
    if (pathname.startsWith('/admin/endpoints')) return 'Endpoints';
    if (pathname.startsWith('/admin/configuration')) return 'Configuration';
    if (pathname.startsWith('/admin/audit-logs')) return 'Audit Logs';
    if (pathname.startsWith('/admin/migrations')) return 'Migrations';
    return 'Admin';
}

export default function AdminLayout() {
    const location = useLocation();

    return (
        <SidebarProvider>
            <AppSidebar />
            <SidebarInset>
                {/* Header */}
                <header className="flex h-16 shrink-0 items-center gap-2 border-b bg-background px-4">
                    <SidebarTrigger className="-ml-1" />
                    <div className="h-4 w-px bg-border mx-2" />
                    <h2 className="text-lg font-semibold">
                        {getAdminPageTitle(location.pathname)}
                    </h2>
                    <div className="ml-auto">
                        <ModeToggle />
                    </div>
                </header>

                {/* Page content — collections, workflows, hooks non-list use full-bleed shell */}
                <main
                    className={
                        isFullBleedAdminPath(location.pathname)
                            ? 'flex flex-1 min-h-0 min-w-0 flex-col overflow-hidden bg-background p-0'
                            : 'flex-1 min-w-0 overflow-y-auto bg-background p-6'
                    }
                >
                    <Outlet />
                </main>
            </SidebarInset>
        </SidebarProvider>
    );
}
