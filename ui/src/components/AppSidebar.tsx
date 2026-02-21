
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
} from "lucide-react"
import { useLocation, Link, useNavigate } from "react-router"
import { useAuthStore } from "@/stores/auth.store"
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
} from "@/components/ui/sidebar"

import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { ChevronsUpDown } from "lucide-react"

// Menu items.
const items = [
    {
        title: "Dashboard",
        url: "/admin/dashboard",
        icon: LayoutDashboard,
    },
    {
        title: "Configuration",
        url: "/admin/configuration",
        icon: Settings,
    },
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
        title: "Invitations",
        url: "/admin/invitations",
        icon: Mail,
    },
    {
        title: "Groups",
        url: "/admin/groups",
        icon: UsersRound,
    },
    {
        title: "Collections",
        url: "/admin/collections",
        icon: Database,
    },
    {
        title: "Roles",
        url: "/admin/roles",
        icon: Shield,
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
    {
        title: "Macros",
        url: "/admin/macros",
        icon: CodeXml,
    },
    {
        title: "API Keys",
        url: "/admin/api-keys",
        icon: Key,
        superadminOnly: true,
    },
]

export function AppSidebar() {
    const location = useLocation()
    const navigate = useNavigate()
    const { user, account, logout } = useAuthStore()

    const handleLogout = () => {
        logout()
        navigate("/admin/login")
    }

    return (
        <Sidebar>
            <SidebarHeader>
                <div className="flex h-12 items-center px-4 gap-2">
                    <h1 className="text-xl font-bold">SnackBase</h1>
                    <span className="text-[10px] items-center bg-muted px-1.5 py-0.5 rounded-md font-medium text-muted-foreground mt-1">
                        v0.6.0
                    </span>
                </div>
            </SidebarHeader>
            <SidebarContent>
                <SidebarGroup>
                    <SidebarGroupLabel>Application</SidebarGroupLabel>
                    <SidebarGroupContent>
                        <SidebarMenu>
                            {items.map((item: any) => {
                                if (item.superadminOnly && account?.id !== "00000000-0000-0000-0000-000000000000") {
                                    return null;
                                }
                                return (
                                    <SidebarMenuItem key={item.title}>
                                        <SidebarMenuButton
                                            asChild
                                            isActive={location.pathname === item.url}
                                        >
                                            <Link to={item.url}>
                                                <item.icon />
                                                <span>{item.title}</span>
                                            </Link>
                                        </SidebarMenuButton>
                                    </SidebarMenuItem>
                                );
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
                                side="bottom"
                                align="end"
                                sideOffset={4}
                            >
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
