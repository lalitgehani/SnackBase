import React, { useCallback, useEffect, useState } from "react"

import {
    LayoutDashboard,
    Users,
    UserCog,
    UsersRound,
    Database,
    Shield,
    FileText,
    GitBranch,
    CodeXml,
    LogOut,
    Settings,
    Mail,
    Key,
    Webhook,
    Briefcase,
    Clock,
    Zap,
    Route,
    GitMerge,
    ChevronsUpDown,
    ChevronRight,
    Plug,
    Cookie,
} from "lucide-react"
import { useLocation, Link, useNavigate } from "react-router"
import { useAuthStore } from "@/stores/auth.store"
import { isSuperadminAccount } from "@/lib/auth"
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
    SidebarMenuSub,
    SidebarMenuSubButton,
    SidebarMenuSubItem,
    SidebarRail,
    useSidebar,
} from "@/components/ui/sidebar"
import {
    Collapsible,
    CollapsibleContent,
    CollapsibleTrigger,
} from "@/components/ui/collapsible"

import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { ThemeMenuItems } from "@/components/mode-toggle"

interface NavItem {
    title: string
    url: string
    icon: React.ElementType
    superadminOnly?: boolean
}

interface NavGroup {
    label: string
    icon: React.ElementType
    items: NavItem[]
}

const OPEN_STATE_STORAGE_KEY = "snackbase.sidebar.navOpen"

/**
 * Top-level links that are not nested under a collapsible section.
 */
const topLevelItems: NavItem[] = [
    {
        title: "Dashboard",
        url: "/admin/dashboard",
        icon: LayoutDashboard,
    },
]

/**
 * Collapsible sidebar sections.
 *
 * Ordered by typical admin workflow. Prefer adding items to an existing
 * section over creating a new top-level flat list.
 */
const navigation: NavGroup[] = [
    {
        label: "Data",
        icon: Database,
        items: [
            {
                title: "Collections",
                url: "/admin/collections",
                icon: Database,
            },
            {
                title: "Macros",
                url: "/admin/macros",
                icon: CodeXml,
            },
        ],
    },
    {
        // Tenant → identity triad (users/groups/roles) → onboarding → machine auth
        label: "Access",
        icon: Shield,
        items: [
            {
                title: "Accounts",
                url: "/admin/accounts",
                icon: Users,
            },
            {
                title: "Users",
                url: "/admin/users",
                icon: UserCog,
            },
            {
                title: "Groups",
                url: "/admin/groups",
                icon: UsersRound,
            },
            {
                title: "Roles",
                url: "/admin/roles",
                icon: Shield,
            },
            {
                title: "Invitations",
                url: "/admin/invitations",
                icon: Mail,
            },
            {
                title: "API Keys",
                url: "/admin/api-keys",
                icon: Key,
                superadminOnly: true,
            },
        ],
    },
    {
        // Event reactions → schedules → orchestration → run history
        label: "Automation",
        icon: Zap,
        items: [
            {
                title: "Hooks",
                url: "/admin/hooks",
                icon: Zap,
            },
            {
                title: "Scheduled Tasks",
                url: "/admin/scheduled-tasks",
                icon: Clock,
            },
            {
                title: "Workflows",
                url: "/admin/workflows",
                icon: GitMerge,
            },
            {
                title: "Jobs",
                url: "/admin/jobs",
                icon: Briefcase,
                superadminOnly: true,
            },
        ],
    },
    {
        label: "Integrations",
        icon: Plug,
        items: [
            {
                title: "Webhooks",
                url: "/admin/webhooks",
                icon: Webhook,
            },
            {
                title: "Endpoints",
                url: "/admin/endpoints",
                icon: Route,
            },
        ],
    },
    {
        label: "System",
        icon: Settings,
        items: [
            {
                title: "Configuration",
                url: "/admin/configuration",
                icon: Settings,
            },
            {
                title: "Audit Logs",
                url: "/admin/audit-logs",
                icon: FileText,
            },
            {
                title: "Migrations",
                url: "/admin/migrations",
                icon: GitBranch,
            },
        ],
    },
]

function isNavItemActive(pathname: string, url: string): boolean {
    if (pathname === url) return true
    // Highlight parent nav for nested routes (e.g. collection detail tabs)
    if (url !== "/admin/dashboard" && pathname.startsWith(`${url}/`)) return true
    return false
}

function groupContainsActivePath(group: NavGroup, pathname: string): boolean {
    return group.items.some((item) => isNavItemActive(pathname, item.url))
}

function readStoredOpenState(): Record<string, boolean> {
    try {
        const raw = localStorage.getItem(OPEN_STATE_STORAGE_KEY)
        if (!raw) return {}
        const parsed: unknown = JSON.parse(raw)
        if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
            return parsed as Record<string, boolean>
        }
    } catch {
        // ignore corrupt storage
    }
    return {}
}

function writeStoredOpenState(state: Record<string, boolean>) {
    try {
        localStorage.setItem(OPEN_STATE_STORAGE_KEY, JSON.stringify(state))
    } catch {
        // ignore quota / private mode
    }
}

function buildInitialOpenState(pathname: string): Record<string, boolean> {
    const stored = readStoredOpenState()
    const next: Record<string, boolean> = {}
    for (const group of navigation) {
        // Always expand the section that owns the current route; otherwise
        // restore the user's last toggle preference (default collapsed).
        next[group.label] =
            groupContainsActivePath(group, pathname) || stored[group.label] === true
    }
    return next
}

function NavGroupItem({
    group,
    visibleItems,
    isOpen,
    onOpenChange,
    pathname,
}: {
    group: NavGroup
    visibleItems: NavItem[]
    isOpen: boolean
    onOpenChange: (open: boolean) => void
    pathname: string
}) {
    const { state, isMobile } = useSidebar()
    const hasActiveChild = groupContainsActivePath(group, pathname)
    // Icon-collapsed desktop rail: flyout dropdown instead of inline sub-tree
    const useFlyout = state === "collapsed" && !isMobile

    if (useFlyout) {
        return (
            <SidebarMenuItem>
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        {/* No tooltip prop: DropdownMenuTrigger asChild cannot wrap Tooltip */}
                        <SidebarMenuButton isActive={hasActiveChild}>
                            <group.icon />
                            <span>{group.label}</span>
                        </SidebarMenuButton>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent
                        side="right"
                        align="start"
                        sideOffset={4}
                        className="min-w-48 rounded-lg"
                    >
                        <DropdownMenuLabel className="text-muted-foreground text-xs">
                            {group.label}
                        </DropdownMenuLabel>
                        {visibleItems.map((item) => (
                            <DropdownMenuItem key={item.title} asChild>
                                <Link to={item.url}>
                                    <item.icon />
                                    <span>{item.title}</span>
                                </Link>
                            </DropdownMenuItem>
                        ))}
                    </DropdownMenuContent>
                </DropdownMenu>
            </SidebarMenuItem>
        )
    }

    // Matches ShadCN sidebar nested menu pattern:
    // https://ui.shadcn.com/docs/components/radix/sidebar
    return (
        <Collapsible
            asChild
            open={isOpen}
            onOpenChange={onOpenChange}
            className="group/collapsible"
        >
            <SidebarMenuItem>
                <CollapsibleTrigger asChild>
                    <SidebarMenuButton
                        tooltip={group.label}
                        isActive={hasActiveChild && !isOpen}
                    >
                        <group.icon />
                        <span>{group.label}</span>
                        <ChevronRight className="ml-auto transition-transform duration-200 group-data-[state=open]/collapsible:rotate-90" />
                    </SidebarMenuButton>
                </CollapsibleTrigger>
                <CollapsibleContent>
                    <SidebarMenuSub>
                        {visibleItems.map((item) => (
                            <SidebarMenuSubItem key={item.title}>
                                <SidebarMenuSubButton
                                    asChild
                                    isActive={isNavItemActive(pathname, item.url)}
                                >
                                    <Link to={item.url}>
                                        <span>{item.title}</span>
                                    </Link>
                                </SidebarMenuSubButton>
                            </SidebarMenuSubItem>
                        ))}
                    </SidebarMenuSub>
                </CollapsibleContent>
            </SidebarMenuItem>
        </Collapsible>
    )
}

export function AppSidebar() {
    const location = useLocation()
    const navigate = useNavigate()
    const { state, isMobile } = useSidebar()
    const { user, account, logout } = useAuthStore()
    const isSuperadmin = isSuperadminAccount(account)
    const isIconCollapsed = state === "collapsed" && !isMobile

    const [openGroups, setOpenGroups] = useState<Record<string, boolean>>(() =>
        buildInitialOpenState(location.pathname),
    )

    // Keep the active section expanded when the route changes
    useEffect(() => {
        setOpenGroups((prev) => {
            let changed = false
            const next = { ...prev }
            for (const group of navigation) {
                if (groupContainsActivePath(group, location.pathname) && !next[group.label]) {
                    next[group.label] = true
                    changed = true
                }
            }
            if (changed) writeStoredOpenState(next)
            return changed ? next : prev
        })
    }, [location.pathname])

    const handleOpenChange = useCallback((label: string, open: boolean) => {
        setOpenGroups((prev) => {
            const next = { ...prev, [label]: open }
            writeStoredOpenState(next)
            return next
        })
    }, [])

    const handleLogout = () => {
        logout()
        navigate("/admin/login")
    }

    return (
        <Sidebar collapsible="icon">
            <SidebarHeader>
                <SidebarMenu>
                    <SidebarMenuItem>
                        {/* Non-interactive brand mark (avoids stealing dialog focus on mobile) */}
                        <div className="flex h-12 items-center gap-2 overflow-hidden rounded-md px-2 group-data-[collapsible=icon]:size-8! group-data-[collapsible=icon]:p-2!">
                            <div className="bg-sidebar-primary text-sidebar-primary-foreground flex aspect-square size-8 items-center justify-center rounded-lg">
                                <Cookie className="size-4" />
                            </div>
                            <div className="grid flex-1 text-left text-sm leading-tight group-data-[collapsible=icon]:hidden">
                                <span className="truncate font-semibold">SnackBase</span>
                                <span className="truncate text-xs text-muted-foreground">
                                    v0.7.1
                                </span>
                            </div>
                        </div>
                    </SidebarMenuItem>
                </SidebarMenu>
            </SidebarHeader>
            <SidebarContent>
                <SidebarGroup>
                    <SidebarGroupLabel>Application</SidebarGroupLabel>
                    <SidebarGroupContent>
                        <SidebarMenu>
                            {/* Top-level flat links (Dashboard) */}
                            {topLevelItems.map((item) => (
                                <SidebarMenuItem key={item.title}>
                                    <SidebarMenuButton
                                        asChild
                                        isActive={isNavItemActive(
                                            location.pathname,
                                            item.url,
                                        )}
                                        tooltip={item.title}
                                    >
                                        <Link to={item.url}>
                                            <item.icon />
                                            <span>{item.title}</span>
                                        </Link>
                                    </SidebarMenuButton>
                                </SidebarMenuItem>
                            ))}

                            {/* Collapsible sections (expand inline, or flyout when icon-collapsed) */}
                            {navigation.map((group) => {
                                const visibleItems = group.items.filter(
                                    (item) => !item.superadminOnly || isSuperadmin,
                                )
                                if (visibleItems.length === 0) return null

                                return (
                                    <NavGroupItem
                                        key={group.label}
                                        group={group}
                                        visibleItems={visibleItems}
                                        isOpen={openGroups[group.label] ?? false}
                                        onOpenChange={(open) =>
                                            handleOpenChange(group.label, open)
                                        }
                                        pathname={location.pathname}
                                    />
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
                                    tooltip={user?.email ?? "Account"}
                                >
                                    <Avatar className="h-8 w-8 rounded-lg">
                                        <AvatarFallback className="rounded-lg">
                                            {user?.email?.charAt(0).toUpperCase()}
                                        </AvatarFallback>
                                    </Avatar>
                                    <div className="grid flex-1 text-left text-sm leading-tight">
                                        <span className="truncate font-semibold">{user?.email}</span>
                                        <span className="truncate text-xs">{user?.role}</span>
                                    </div>
                                    <ChevronsUpDown className="ml-auto size-4" />
                                </SidebarMenuButton>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent
                                className="w-[--radix-dropdown-menu-trigger-width] min-w-56 rounded-lg"
                                side={isIconCollapsed ? "right" : "bottom"}
                                align="end"
                                sideOffset={4}
                            >
                                <DropdownMenuLabel className="p-0 font-normal">
                                    <div className="flex items-center gap-2 px-1 py-1.5 text-left text-sm">
                                        <Avatar className="h-8 w-8 rounded-lg">
                                            <AvatarFallback className="rounded-lg">
                                                {user?.email?.charAt(0).toUpperCase()}
                                            </AvatarFallback>
                                        </Avatar>
                                        <div className="grid flex-1 text-left text-sm leading-tight">
                                            <span className="truncate font-semibold">
                                                {user?.email}
                                            </span>
                                            <span className="truncate text-xs text-muted-foreground">
                                                {user?.role}
                                            </span>
                                        </div>
                                    </div>
                                </DropdownMenuLabel>
                                <DropdownMenuSeparator />
                                <ThemeMenuItems />
                                <DropdownMenuSeparator />
                                <DropdownMenuItem onClick={handleLogout}>
                                    <LogOut className="mr-2 h-4 w-4" />
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
