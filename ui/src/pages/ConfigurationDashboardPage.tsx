import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { adminService } from '@/services/admin.service';
import type { Configuration, ConfigurationStats } from '@/services/admin.service';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Plus, Activity, Server, Users, Settings } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { formatDistanceToNow } from 'date-fns';

const ConfigurationDashboardPage = () => {
    const { data: stats, isLoading: statsLoading } = useQuery<ConfigurationStats>({
        queryKey: ['admin', 'config', 'stats'],
        queryFn: adminService.getStats,
        refetchInterval: 30000, // Auto-refresh every 30s as per requirement
    });

    const { data: recentConfigs, isLoading: recentLoading } = useQuery<Configuration[]>({
        queryKey: ['admin', 'config', 'recent'],
        queryFn: () => adminService.getRecentConfigs(5),
        refetchInterval: 30000,
    });

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Configuration</h1>
                    <p className="text-muted-foreground">
                        Manage system and account-level provider configurations.
                    </p>
                </div>
            </div>

            {/* Overview Cards */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">System Configs</CardTitle>
                        <Server className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        {statsLoading ? (
                            <Skeleton className="h-8 w-[100px]" />
                        ) : (
                            <>
                                <div className="text-2xl font-bold">{stats?.system_configs.total || 0}</div>
                                <p className="text-xs text-muted-foreground">
                                    Active system-level providers
                                </p>
                            </>
                        )}
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Account Configs</CardTitle>
                        <Users className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        {statsLoading ? (
                            <Skeleton className="h-8 w-[100px]" />
                        ) : (
                            <>
                                <div className="text-2xl font-bold">{stats?.account_configs.total || 0}</div>
                                <p className="text-xs text-muted-foreground">
                                    Active account-level overrides
                                </p>
                            </>
                        )}
                    </CardContent>
                </Card>

                {/* Categories Breakdown (Aggregated) */}
                <Card className="col-span-2">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Category Breakdown</CardTitle>
                        <Activity className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        {statsLoading ? (
                            <div className="flex gap-4">
                                <Skeleton className="h-8 w-[100px]" />
                                <Skeleton className="h-8 w-[100px]" />
                                <Skeleton className="h-8 w-[100px]" />
                            </div>
                        ) : (
                            <div className="flex gap-6 mt-2">
                                {Object.entries(stats?.system_configs.by_category || {}).map(([category, count]) => (
                                    <div key={`sys-${category}`} className="flex flex-col">
                                        <span className="text-xs text-muted-foreground uppercase">{category.replace('_', ' ')}</span>
                                        <span className="font-bold">{count} <span className="text-xs font-normal text-muted-foreground">(Sys)</span></span>
                                    </div>
                                ))}
                                {Object.entries(stats?.account_configs.by_category || {}).map(([category, count]) => (
                                    <div key={`acc-${category}`} className="flex flex-col">
                                        <span className="text-xs text-muted-foreground uppercase">{category.replace('_', ' ')}</span>
                                        <span className="font-bold">{count} <span className="text-xs font-normal text-muted-foreground">(Acc)</span></span>
                                    </div>
                                ))}
                                {(!stats?.system_configs.by_category && !stats?.account_configs.by_category) && (
                                    <span className="text-sm text-muted-foreground">No active configurations</span>
                                )}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
                {/* Recent Activity */}
                <Card className="col-span-4">
                    <CardHeader>
                        <CardTitle>Recent Activity</CardTitle>
                        <CardDescription>
                            Recently modified configurations.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {recentLoading ? (
                            <div className="space-y-4">
                                <Skeleton className="h-12 w-full" />
                                <Skeleton className="h-12 w-full" />
                                <Skeleton className="h-12 w-full" />
                            </div>
                        ) : (
                            <div className="space-y-4">
                                {recentConfigs && recentConfigs.length > 0 ? (
                                    recentConfigs.map((config) => (
                                        <div key={config.id} className="flex items-center justify-between border-b pb-2 last:border-0 last:pb-0">
                                            <div className="flex items-center gap-4">
                                                {config.logo_url ? (
                                                    <img src={config.logo_url} alt={config.provider_name} className="h-8 w-8 object-contain" />
                                                ) : (
                                                    <div className="h-8 w-8 bg-secondary rounded-full flex items-center justify-center">
                                                        <Settings className="h-4 w-4" />
                                                    </div>
                                                )}
                                                <div>
                                                    <p className="font-medium">{config.display_name}</p>
                                                    <p className="text-xs text-muted-foreground">
                                                        {config.is_system ? 'System' : 'Account'} • {config.category}
                                                    </p>
                                                </div>
                                            </div>
                                            <div className="text-xs text-muted-foreground">
                                                {formatDistanceToNow(new Date(config.updated_at), { addSuffix: true })}
                                            </div>
                                        </div>
                                    ))
                                ) : (
                                    <div className="text-center py-4 text-muted-foreground">
                                        No recent activity found.
                                    </div>
                                )}
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Quick Actions */}
                <Card className="col-span-3">
                    <CardHeader>
                        <CardTitle>Quick Actions</CardTitle>
                        <CardDescription>
                            Manage your provider configurations.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <Button className="w-full justify-start" variant="outline">
                            <Plus className="mr-2 h-4 w-4" />
                            Add System Config
                        </Button>
                        <Button className="w-full justify-start" variant="outline">
                            <Plus className="mr-2 h-4 w-4" />
                            Add Account Config
                        </Button>
                        <div className="pt-4">
                            <p className="text-xs text-muted-foreground mb-2">
                                Use System Configs to set global defaults for all accounts. Use Account Configs to override settings for specific tenants.
                            </p>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
};

export default ConfigurationDashboardPage;
