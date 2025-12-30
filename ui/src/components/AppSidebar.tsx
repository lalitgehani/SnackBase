
import {
    LayoutDashboard,
    Users,
    UserCog,
    UsersRound,
    Database,
    Shield,
    FileText,
    LogOut,
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
]

export function AppSidebar() {
    const location = useLocation()
    const navigate = useNavigate()
    const { user, logout } = useAuthStore()

    const handleLogout = () => {
        logout()
        navigate("/admin/login")
    }

    return (
        <Sidebar>
            <SidebarHeader>
                <div className="flex h-12 items-center px-4">
                    <h1 className="text-xl font-bold">SnackBase</h1>
                </div>
            </SidebarHeader>
            <SidebarContent>
                <SidebarGroup>
                    <SidebarGroupLabel>Application</SidebarGroupLabel>
                    <SidebarGroupContent>
                        <SidebarMenu>
                            {items.map((item) => (
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
                            ))}
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
