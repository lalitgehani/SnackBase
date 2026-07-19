/**
 * Admin layout with sidebar navigation
 */

import { Outlet, useLocation } from 'react-router';
import { SidebarInset, SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar';
import { AppSidebar } from '@/components/AppSidebar';
import { ModeToggle } from '@/components/mode-toggle';

export default function AdminLayout() {
    const location = useLocation();

    // Map current path to page title (keep in sync with AppSidebar nav items)
    const getPageTitle = () => {
        if (location.pathname === '/admin/dashboard') return 'Dashboard';
        if (location.pathname.startsWith('/admin/collections')) return 'Collections';
        if (location.pathname.startsWith('/admin/macros')) return 'Macros';
        if (location.pathname.startsWith('/admin/accounts')) return 'Accounts';
        if (location.pathname.startsWith('/admin/users')) return 'Users';
        if (location.pathname.startsWith('/admin/groups')) return 'Groups';
        if (location.pathname.startsWith('/admin/roles')) return 'Roles';
        if (location.pathname.startsWith('/admin/invitations')) return 'Invitations';
        if (location.pathname.startsWith('/admin/api-keys')) return 'API Keys';
        if (location.pathname.startsWith('/admin/hooks')) return 'Hooks';
        if (location.pathname.startsWith('/admin/scheduled-tasks')) return 'Scheduled Tasks';
        if (location.pathname.startsWith('/admin/workflows')) return 'Workflows';
        if (location.pathname.startsWith('/admin/jobs')) return 'Jobs';
        if (location.pathname.startsWith('/admin/webhooks')) return 'Webhooks';
        if (location.pathname.startsWith('/admin/endpoints')) return 'Endpoints';
        if (location.pathname.startsWith('/admin/configuration')) return 'Configuration';
        if (location.pathname.startsWith('/admin/audit-logs')) return 'Audit Logs';
        if (location.pathname.startsWith('/admin/migrations')) return 'Migrations';
        return 'Admin';
    };

    return (
        <SidebarProvider>
            <AppSidebar />
            <SidebarInset>
                {/* Header */}
                <header className="flex h-16 shrink-0 items-center gap-2 border-b bg-background px-4">
                    <SidebarTrigger className="-ml-1" />
                    <div className="h-4 w-px bg-border mx-2" />
                    <h2 className="text-lg font-semibold">
                        {getPageTitle()}
                    </h2>
                    <div className="ml-auto">
                        <ModeToggle />
                    </div>
                </header>

                {/* Page content — collections workspace uses full-bleed shell */}
                <main
                    className={
                        location.pathname.startsWith('/admin/collections')
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
