/**
 * Admin layout with sidebar navigation
 */

import { useState } from 'react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router';
import {
    LayoutDashboard,
    Users,
    UserCog,
    Database,
    Shield,
    FileText,
    LogOut,
    Menu,
    X
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/stores/auth.store';
import { cn } from '@/lib/utils';

const navigation = [
    { name: 'Dashboard', href: '/admin/dashboard', icon: LayoutDashboard },
    { name: 'Accounts', href: '/admin/accounts', icon: Users },
    { name: 'Users', href: '/admin/users', icon: UserCog },
    { name: 'Collections', href: '/admin/collections', icon: Database },
    { name: 'Roles', href: '/admin/roles', icon: Shield },
    { name: 'Audit Logs', href: '/admin/audit-logs', icon: FileText },
];

export default function AdminLayout() {
    const location = useLocation();
    const navigate = useNavigate();
    const { user, logout } = useAuthStore();
    const [sidebarOpen, setSidebarOpen] = useState(false);

    const handleLogout = () => {
        logout();
        navigate('/admin/login');
    };

    return (
        <div className="flex h-screen bg-background">
            {/* Mobile sidebar backdrop */}
            {sidebarOpen && (
                <div
                    className="fixed inset-0 z-40 bg-black/50 lg:hidden"
                    onClick={() => setSidebarOpen(false)}
                />
            )}

            {/* Sidebar */}
            <aside
                className={cn(
                    'fixed inset-y-0 left-0 z-50 w-64 transform bg-card border-r transition-transform duration-300 ease-in-out lg:static lg:translate-x-0',
                    sidebarOpen ? 'translate-x-0' : '-translate-x-full'
                )}
            >
                <div className="flex h-full flex-col">
                    {/* Logo */}
                    <div className="flex h-16 items-center justify-between px-6 border-b">
                        <h1 className="text-xl font-bold">
                            SnackBase
                        </h1>
                        <button
                            className="lg:hidden text-muted-foreground hover:text-foreground"
                            onClick={() => setSidebarOpen(false)}
                        >
                            <X className="h-6 w-6" />
                        </button>
                    </div>

                    {/* Navigation */}
                    <nav className="flex-1 space-y-1 px-3 py-4">
                        {navigation.map((item) => {
                            const isActive = location.pathname === item.href;
                            return (
                                <Link
                                    key={item.name}
                                    to={item.href}
                                    className={cn(
                                        'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                                        isActive
                                            ? 'bg-primary text-primary-foreground'
                                            : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                                    )}
                                    onClick={() => setSidebarOpen(false)}
                                >
                                    <item.icon className="h-5 w-5" />
                                    {item.name}
                                </Link>
                            );
                        })}
                    </nav>

                    {/* User info & logout */}
                    <div className="border-t p-4">
                        <div className="mb-3 rounded-lg bg-muted p-3">
                            <p className="text-xs text-muted-foreground">Signed in as</p>
                            <p className="text-sm font-medium truncate">{user?.email}</p>
                            <p className="text-xs text-primary mt-1">{user?.role}</p>
                        </div>
                        <Button
                            variant="outline"
                            className="w-full"
                            onClick={handleLogout}
                        >
                            <LogOut className="mr-2 h-4 w-4" />
                            Logout
                        </Button>
                    </div>
                </div>
            </aside>

            {/* Main content */}
            <div className="flex flex-1 flex-col overflow-hidden">
                {/* Header */}
                <header className="flex h-16 items-center justify-between border-b bg-card px-6">
                    <button
                        className="lg:hidden text-muted-foreground hover:text-foreground"
                        onClick={() => setSidebarOpen(true)}
                    >
                        <Menu className="h-6 w-6" />
                    </button>
                    <div className="flex-1 lg:flex-none">
                        <h2 className="text-lg font-semibold">
                            {navigation.find((item) => item.href === location.pathname)?.name || 'Admin'}
                        </h2>
                    </div>
                </header>

                {/* Page content */}
                <main className="flex-1 overflow-y-auto bg-background p-6">
                    <Outlet />
                </main>
            </div>
        </div>
    );
}
