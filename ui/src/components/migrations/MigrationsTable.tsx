import { Badge } from '@/components/ui/badge';
import { format } from 'date-fns';
import type { MigrationRevision } from '@/types/migrations';
import { DataTable, type Column } from '@/components/common/DataTable';
import MigrationStatusBadge from './MigrationStatusBadge';

interface MigrationsTableProps {
    migrations: MigrationRevision[];
    currentRevision: string | null;
    onView: (migration: MigrationRevision) => void;
    isLoading?: boolean;
}

export default function MigrationsTable({
    migrations,
    currentRevision,
    onView,
    isLoading,
}: MigrationsTableProps) {
    const columns: Column<MigrationRevision>[] = [
        {
            header: 'Revision',
            accessorKey: 'revision',
            className: 'font-mono text-xs max-w-[120px]',
            render: (migration) => (
                <span
                    className="truncate block"
                    title={migration.revision}
                >
                    {migration.revision.substring(0, 12)}
                </span>
            ),
        },
        {
            header: 'Description',
            accessorKey: 'description',
            className: 'font-medium',
        },
        {
            header: 'Type',
            render: (migration) => (
                <Badge
                    variant={migration.is_dynamic ? 'secondary' : 'outline'}
                    className={migration.is_dynamic ? 'bg-purple-500 hover:bg-purple-600 text-white' : ''}
                >
                    {migration.is_dynamic ? 'Dynamic' : 'Core'}
                </Badge>
            ),
        },
        {
            header: 'Status',
            render: (migration) => (
                <MigrationStatusBadge
                    isApplied={migration.is_applied}
                    isHead={migration.is_head}
                    isCurrent={migration.revision === currentRevision}
                />
            ),
        },
        {
            header: 'Created',
            accessorKey: 'created_at',
            sortable: true,
            className: 'whitespace-nowrap',
            render: (migration) =>
                migration.created_at
                    ? format(new Date(migration.created_at), 'yyyy-MM-dd HH:mm')
                    : '-',
        },
        {
            header: 'Branch Labels',
            render: (migration) =>
                migration.branch_labels && migration.branch_labels.length > 0 ? (
                    <div className="flex gap-1 flex-wrap">
                        {migration.branch_labels.map((label) => (
                            <Badge key={label} variant="outline" className="text-xs">
                                {label}
                            </Badge>
                        ))}
                    </div>
                ) : (
                    <span className="text-muted-foreground">-</span>
                ),
        },
    ];

    return (
        <DataTable
            data={migrations}
            columns={columns}
            keyExtractor={(migration) => migration.revision}
            isLoading={isLoading}
            totalItems={migrations.length}
            onRowClick={onView}
            noDataMessage="No migrations found."
        />
    );
}
