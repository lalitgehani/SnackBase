import { Outlet, useLocation } from 'react-router';
import { SidebarInset, SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar';
import { AppSidebar } from '@/components/AppSidebar';
import { PlatformStudioChrome } from '@/components/platform/PlatformStudioChrome';
import { ModeToggle } from '@/components/mode-toggle';
import { getAdminPageTitle, isFullBleedAdminPath } from '@/layouts/adminLayoutHelpers';
import { normalizeToAdminPath } from '@/lib/platform/studioPath';
import { useStudioBasePath } from '@/lib/platform/StudioBasePathContext';

/**
 * Studio admin layout inside a platform project (F4.3).
 * Reuses AppSidebar with platform chrome and path remapping.
 */
export default function PlatformStudioLayout() {
  const location = useLocation();
  const studioCtx = useStudioBasePath();
  const adminPath = normalizeToAdminPath(location.pathname);
  const pageTitle = getAdminPageTitle(adminPath);

  if (!studioCtx) {
    throw new Error('PlatformStudioLayout requires StudioBasePathProvider');
  }

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <PlatformStudioChrome />
        <header className="flex h-16 shrink-0 items-center gap-2 border-b bg-background px-4">
          <SidebarTrigger className="-ml-1" />
          <div className="mx-2 h-4 w-px bg-border" />
          <h2 className="text-lg font-semibold" data-testid="page-title">
            {pageTitle}
          </h2>
          <div className="ml-auto">
            <ModeToggle />
          </div>
        </header>
        <main
          className={
            isFullBleedAdminPath(adminPath)
              ? 'flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-background p-0'
              : 'min-w-0 flex-1 overflow-y-auto bg-background p-6'
          }
        >
          <Outlet />
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}
