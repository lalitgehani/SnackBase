/**
 * Admin layout with sidebar navigation
 */

import { Outlet, useLocation } from 'react-router';
import { SidebarInset, SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar';
import { AppSidebar } from '@/components/AppSidebar';

export default function AdminLayout() {
    const location = useLocation();

    // Map current path to page title
    const getPageTitle = () => {
        if (location.pathname === '/admin/dashboard') return 'Dashboard';
        if (location.pathname.startsWith('/admin/accounts')) return 'Accounts';
        if (location.pathname.startsWith('/admin/users')) return 'Users';
        if (location.pathname.startsWith('/admin/groups')) return 'Groups';
        if (location.pathname.startsWith('/admin/collections')) return 'Collections';
        if (location.pathname.startsWith('/admin/roles')) return 'Roles';
        if (location.pathname.startsWith('/admin/audit-logs')) return 'Audit Logs';
        if (location.pathname.startsWith('/admin/migrations')) return 'Migrations';
        if (location.pathname.startsWith('/admin/macros')) return 'Macros';
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
                </header>

                {/* Page content */}
                <main className="flex-1 min-w-0 overflow-y-auto bg-background p-6">
                    <Outlet />
                </main>
            </SidebarInset>
        </SidebarProvider>
    );
}
