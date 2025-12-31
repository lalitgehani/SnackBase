/**
 * Migrations management page
 */

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Database, Search, RefreshCw } from 'lucide-react';
import MigrationsTable from '@/components/migrations/MigrationsTable';
import MigrationDetailDialog from '@/components/migrations/MigrationDetailDialog';
import { listMigrations } from '@/services/migrations.service';
import type { MigrationRevision, MigrationListResponse } from '@/types/migrations';
import { handleApiError } from '@/lib/api';

export default function MigrationsPage() {
    const [data, setData] = useState<MigrationListResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Search state
    const [searchQuery, setSearchQuery] = useState('');

    // Dialog state
    const [detailDialogOpen, setDetailDialogOpen] = useState(false);
    const [selectedMigration, setSelectedMigration] = useState<MigrationRevision | null>(null);

    const fetchMigrations = async () => {
        setLoading(true);
        setError(null);

        try {
            const response = await listMigrations();
            setData(response);
        } catch (err) {
            setError(handleApiError(err));
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchMigrations();
    }, []);

    const handleView = (migration: MigrationRevision) => {
        setSelectedMigration(migration);
        setDetailDialogOpen(true);
    };

    // Filter migrations by search query
    const filteredMigrations = data?.revisions.filter((migration) =>
        migration.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        migration.revision.toLowerCase().includes(searchQuery.toLowerCase())
    ) || [];

    // Calculate stats
    const totalMigrations = data?.total || 0;
    const appliedMigrations = data?.revisions.filter((m) => m.is_applied).length || 0;
    const pendingMigrations = totalMigrations - appliedMigrations;
    const dynamicMigrations = data?.revisions.filter((m) => m.is_dynamic).length || 0;
    const coreMigrations = totalMigrations - dynamicMigrations;

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold">Migrations</h1>
                    <p className="text-muted-foreground mt-2">
                        View Alembic migration status and history
                    </p>
                </div>
                <Button
                    variant="outline"
                    onClick={fetchMigrations}
                    disabled={loading}
                    className="gap-2"
                >
                    <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                    Refresh
                </Button>
            </div>

            {/* Stats Cards */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">
                            Total Migrations
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{totalMigrations}</div>
                        <p className="text-xs text-muted-foreground mt-1">
                            {coreMigrations} core, {dynamicMigrations} dynamic
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">
                            Applied
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-green-600">{appliedMigrations}</div>
                        <p className="text-xs text-muted-foreground mt-1">Successfully applied</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">
                            Pending
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-yellow-600">{pendingMigrations}</div>
                        <p className="text-xs text-muted-foreground mt-1">Not yet applied</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">
                            Current Revision
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-sm font-mono truncate" title={data?.current_revision || 'None'}>
                            {data?.current_revision ? data.current_revision.substring(0, 12) : 'None'}
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">Active database state</p>
                    </CardContent>
                </Card>
            </div>


            {/* Migrations Table */}
            <Card>
                <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                        <CardTitle className="flex items-center gap-2">
                            <Database className="h-5 w-5 text-primary" />
                            Migration History
                        </CardTitle>
                    </div>
                    <CardDescription>
                        All Alembic revisions from core and dynamic directories
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    {/* Search Bar */}
                    <div className="flex gap-2">
                        <div className="relative flex-1">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                            <Input
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                placeholder="Search by description or revision..."
                                className="pl-9"
                            />
                        </div>
                        {searchQuery && (
                            <Button
                                variant="outline"
                                onClick={() => setSearchQuery('')}
                            >
                                Clear
                            </Button>
                        )}
                    </div>

                    {/* Error State */}
                    {error && (
                        <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
                            <p className="text-destructive font-medium">Failed to load migrations</p>
                            <p className="text-sm text-muted-foreground mt-1">{error}</p>
                            <Button onClick={fetchMigrations} className="mt-4" size="sm">
                                Try Again
                            </Button>
                        </div>
                    )}

                    {/* Loading State */}
                    {loading && !data && (
                        <div className="flex items-center justify-center py-12">
                            <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
                        </div>
                    )}

                    {/* Table */}
                    {!loading && data && (
                        <>
                            {filteredMigrations.length === 0 && searchQuery ? (
                                <div className="text-center py-12">
                                    <p className="text-muted-foreground">
                                        No migrations found matching "{searchQuery}"
                                    </p>
                                    <Button
                                        variant="link"
                                        onClick={() => setSearchQuery('')}
                                        className="mt-2"
                                    >
                                        Clear search
                                    </Button>
                                </div>
                            ) : (
                                <MigrationsTable
                                    migrations={filteredMigrations}
                                    currentRevision={data.current_revision}
                                    onView={handleView}
                                    isLoading={loading}
                                />
                            )}
                        </>
                    )}
                </CardContent>
            </Card>

            {/* Detail Dialog */}
            <MigrationDetailDialog
                open={detailDialogOpen}
                onOpenChange={setDetailDialogOpen}
                migration={selectedMigration}
                currentRevision={data?.current_revision || null}
            />
        </div>
    );
}
