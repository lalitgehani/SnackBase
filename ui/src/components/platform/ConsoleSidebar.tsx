import {
  Building2,
  FolderKanban,
  Layers,
  LogOut,
  Settings,
  ChevronsUpDown,
} from 'lucide-react'
import { Link, useLocation, useNavigate } from 'react-router'
import { useAuth } from '@snackbase/react'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from '@/components/ui/sidebar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { ThemeMenuItems } from '@/components/mode-toggle'
import { OrgSwitcher } from '@/components/platform/OrgSwitcher'
import {
  isNavActive,
  isOrganizationsNavActive,
  isProjectsNavActive,
} from '@/components/platform/consoleSidebarNav'
import { useOrgContextStore } from '@/stores/org-context.store'

function initials(email?: string | null, name?: string | null): string {
  if (name?.trim()) {
    return name
      .split(/\s+/)
      .map((p) => p[0])
      .join('')
      .slice(0, 2)
      .toUpperCase()
  }
  if (email) return email.slice(0, 2).toUpperCase()
  return '?'
}

export function ConsoleSidebar() {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, account, logout } = useAuth()
  const { activeOrg, clearActiveOrg } = useOrgContextStore()

  const projectsUrl = activeOrg
    ? `/organizations/${activeOrg.id}/projects`
    : '/organizations'

  const navItems = [
    {
      title: 'Organizations',
      url: '/organizations',
      icon: Building2,
      testId: 'nav-organizations',
      // Do not prefix-match nested /organizations/:id/projects… routes
      match: isOrganizationsNavActive,
    },
    {
      title: 'Projects',
      url: projectsUrl,
      icon: FolderKanban,
      testId: 'nav-projects',
      // Highlight when under any org projects path
      match: isProjectsNavActive,
    },
    {
      title: 'Account',
      url: '/account',
      icon: Settings,
      testId: 'nav-account',
    },
  ]

  const handleLogout = async () => {
    clearActiveOrg()
    await logout()
    navigate('/login')
  }

  const email = user?.email ?? ''
  const displayName = (user as { name?: string } | null)?.name ?? email

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <Link to="/organizations">
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                  <Layers className="size-4" />
                </div>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-semibold">SnackBase Cloud</span>
                  <span className="truncate text-xs text-muted-foreground">
                    {account?.slug ?? account?.id ?? 'Console'}
                  </span>
                </div>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
        <OrgSwitcher />
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Workspace</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => {
                const active = item.match
                  ? item.match(location.pathname)
                  : isNavActive(location.pathname, item.url)
                return (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton
                      asChild
                      isActive={active}
                      tooltip={item.title}
                      data-testid={item.testId}
                    >
                      <Link to={item.url}>
                        <item.icon />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                )
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuButton
                  size="lg"
                  className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
                  data-testid="user-menu"
                >
                  <Avatar className="h-8 w-8 rounded-lg">
                    <AvatarFallback className="rounded-lg">
                      {initials(email, displayName)}
                    </AvatarFallback>
                  </Avatar>
                  <div className="grid flex-1 text-left text-sm leading-tight">
                    <span className="truncate font-semibold">{displayName}</span>
                    <span className="truncate text-xs text-muted-foreground">
                      {email}
                    </span>
                  </div>
                  <ChevronsUpDown className="ml-auto size-4" />
                </SidebarMenuButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                className="w-[--radix-dropdown-menu-trigger-width] min-w-56 rounded-lg"
                side="top"
                align="end"
                sideOffset={4}
              >
                <DropdownMenuLabel className="p-0 font-normal">
                  <div className="flex items-center gap-2 px-1 py-1.5 text-left text-sm">
                    <Avatar className="h-8 w-8 rounded-lg">
                      <AvatarFallback className="rounded-lg">
                        {initials(email, displayName)}
                      </AvatarFallback>
                    </Avatar>
                    <div className="grid flex-1 text-left text-sm leading-tight">
                      <span className="truncate font-semibold">{displayName}</span>
                      <span className="truncate text-xs text-muted-foreground">
                        {email}
                      </span>
                    </div>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link to="/account">
                    <Settings />
                    Account settings
                  </Link>
                </DropdownMenuItem>
                <ThemeMenuItems />
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout} data-testid="logout-button">
                  <LogOut />
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
