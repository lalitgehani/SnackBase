/**
 * Dashboard page - main landing page after login
 */

import { useAuthStore } from '@/stores/auth.store';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { LayoutDashboard } from 'lucide-react';

export default function DashboardPage() {
    const { user, account } = useAuthStore();

    return (
        <div className="space-y-6">
            {/* Welcome section */}
            <div>
                <h1 className="text-3xl font-bold">Welcome back!</h1>
                <p className="text-muted-foreground mt-2">
                    Logged in as <span className="text-primary font-medium">{user?.email}</span>
                </p>
            </div>

            {/* Account info */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <LayoutDashboard className="h-5 w-5 text-primary" />
                        System Information
                    </CardTitle>
                    <CardDescription>
                        Current account and user details
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="rounded-lg bg-muted p-4 border">
                            <p className="text-xs text-muted-foreground mb-1">Account ID</p>
                            <p className="text-sm font-mono">{account?.id}</p>
                        </div>
                        <div className="rounded-lg bg-muted p-4 border">
                            <p className="text-xs text-muted-foreground mb-1">Account Name</p>
                            <p className="text-sm">{account?.name}</p>
                        </div>
                        <div className="rounded-lg bg-muted p-4 border">
                            <p className="text-xs text-muted-foreground mb-1">User Role</p>
                            <p className="text-sm text-primary font-medium">{user?.role}</p>
                        </div>
                        <div className="rounded-lg bg-muted p-4 border">
                            <p className="text-xs text-muted-foreground mb-1">Status</p>
                            <p className="text-sm text-green-600 dark:text-green-400 font-medium">
                                {user?.is_active ? 'Active' : 'Inactive'}
                            </p>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Coming soon section */}
            <Card>
                <CardHeader>
                    <CardTitle>Dashboard Metrics</CardTitle>
                    <CardDescription>
                        Coming in Phase 3.2
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <p className="text-muted-foreground">
                        The dashboard will display key metrics including total accounts, users, collections,
                        records, and recent activity. This feature will be implemented in the next phase.
                    </p>
                </CardContent>
            </Card>
        </div>
    );
}
