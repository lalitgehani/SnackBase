import { Outlet, useLocation } from 'react-router'
import { SidebarInset, SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar'
import { ConsoleSidebar } from '@/components/platform/ConsoleSidebar'
import { ModeToggle } from '@/components/mode-toggle'
import { getConsolePageTitle } from '@/layouts/platform/consoleLayoutHelpers'

export default function ConsoleLayout() {
  const location = useLocation()

  return (
    <SidebarProvider>
      <ConsoleSidebar />
      <SidebarInset>
        <header className="flex h-16 shrink-0 items-center gap-2 border-b bg-background px-4">
          <SidebarTrigger className="-ml-1" />
          <div className="mx-2 h-4 w-px bg-border" />
          <h2 className="text-lg font-semibold" data-testid="page-title">
            {getConsolePageTitle(location.pathname)}
          </h2>
          <div className="ml-auto">
            <ModeToggle />
          </div>
        </header>
        <main className="min-w-0 flex-1 overflow-y-auto bg-background p-6">
          <Outlet />
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}
