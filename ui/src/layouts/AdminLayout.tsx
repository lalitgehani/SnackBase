/**
 * Admin layout with sidebar navigation
 */

import { Outlet, useLocation } from 'react-router';
import { SidebarInset, SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar';
import { AppSidebar } from '@/components/AppSidebar';
import { ModeToggle } from '@/components/mode-toggle';
import { getAdminPageTitle, isFullBleedAdminPath } from '@/layouts/adminLayoutHelpers';

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
