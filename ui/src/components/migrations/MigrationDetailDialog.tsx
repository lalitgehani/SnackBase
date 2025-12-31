/**
 * Migration detail dialog component
 */

import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import type { MigrationRevision } from '@/types/migrations';
import { format } from 'date-fns';
import { Database, Clock, GitBranch, FileCode, Copy, Check } from 'lucide-react';
import { useState } from 'react';
import MigrationStatusBadge from './MigrationStatusBadge';

interface MigrationDetailDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    migration: MigrationRevision | null;
    currentRevision: string | null;
}

export default function MigrationDetailDialog({
    open,
    onOpenChange,
    migration,
    currentRevision,
}: MigrationDetailDialogProps) {
    const [copiedRevision, setCopiedRevision] = useState(false);

    if (!migration) return null;

    const handleCopyRevision = async () => {
        await navigator.clipboard.writeText(migration.revision);
        setCopiedRevision(true);
        setTimeout(() => setCopiedRevision(false), 2000);
    };

    const DetailItem = ({
        label,
        value,
        icon: Icon,
        mono = false,
    }: {
        label: string;
        value: any;
        icon?: any;
        mono?: boolean;
    }) => (
        <div className="flex flex-col space-y-1 py-2">
            <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                {Icon && <Icon className="h-4 w-4" />}
                {label}
            </div>
            <div className={`text-sm break-all font-medium ${mono ? 'font-mono' : ''}`}>
                {value || <span className="text-muted-foreground italic">None</span>}
            </div>
        </div>
    );

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-4xl max-h-[90vh]">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        Migration: {migration.revision.substring(0, 12)}
                        <MigrationStatusBadge
                            isApplied={migration.is_applied}
                            isHead={migration.is_head}
                            isCurrent={migration.revision === currentRevision}
                        />
                    </DialogTitle>
                    <DialogDescription>{migration.description}</DialogDescription>
                </DialogHeader>

                <ScrollArea className="pr-4 h-full">
                    <div className="space-y-6 py-4">
                        {/* Summary Section */}
                        <div className="grid grid-cols-2 gap-4">
                            <div className="flex flex-col space-y-1 py-2">
                                <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                                    <Database className="h-4 w-4" />
                                    Revision Hash
                                </div>
                                <div className="flex items-center gap-2">
                                    <code className="text-sm font-mono bg-muted px-2 py-1 rounded">
                                        {migration.revision}
                                    </code>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="h-6 w-6"
                                        onClick={handleCopyRevision}
                                    >
                                        {copiedRevision ? (
                                            <Check className="h-3 w-3 text-green-500" />
                                        ) : (
                                            <Copy className="h-3 w-3" />
                                        )}
                                    </Button>
                                </div>
                            </div>

                            <DetailItem
                                label="Created At"
                                value={
                                    migration.created_at
                                        ? format(new Date(migration.created_at), 'yyyy-MM-dd HH:mm:ss')
                                        : 'Unknown'
                                }
                                icon={Clock}
                            />

                            <div className="flex flex-col space-y-1 py-2">
                                <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                                    <FileCode className="h-4 w-4" />
                                    Migration Type
                                </div>
                                <Badge
                                    variant={migration.is_dynamic ? 'secondary' : 'outline'}
                                    className={
                                        migration.is_dynamic
                                            ? 'bg-purple-500 hover:bg-purple-600 text-white w-fit'
                                            : 'w-fit'
                                    }
                                >
                                    {migration.is_dynamic ? 'Dynamic (Auto-generated)' : 'Core (Manual)'}
                                </Badge>
                            </div>

                            <div className="flex flex-col space-y-1 py-2">
                                <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                                    <FileCode className="h-4 w-4" />
                                    File Path
                                </div>
                                <code className="text-xs font-mono bg-muted px-2 py-1 rounded break-all">
                                    alembic/versions/{migration.is_dynamic ? 'dynamic' : 'core'}/
                                    {migration.revision}_{migration.description.toLowerCase().replace(/\s+/g, '_')}.py
                                </code>
                            </div>
                        </div>

                        <Separator />

                        {/* Revision Chain */}
                        <div>
                            <h3 className="flex items-center gap-2 text-sm font-bold uppercase text-primary mb-4">
                                <GitBranch className="h-4 w-4" />
                                Revision Chain
                            </h3>
                            <div className="grid grid-cols-2 gap-4">
                                <DetailItem
                                    label="Revises (Previous)"
                                    value={migration.down_revision || 'None (Initial migration)'}
                                    mono
                                />
                                <div className="flex flex-col space-y-1 py-2">
                                    <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                                        Branch Labels
                                    </div>
                                    {migration.branch_labels && migration.branch_labels.length > 0 ? (
                                        <div className="flex gap-1 flex-wrap">
                                            {migration.branch_labels.map((label) => (
                                                <Badge key={label} variant="outline">
                                                    {label}
                                                </Badge>
                                            ))}
                                        </div>
                                    ) : (
                                        <span className="text-sm text-muted-foreground italic">None</span>
                                    )}
                                </div>
                            </div>
                        </div>

                        <Separator />

                        {/* SQL Information */}
                        <div className="space-y-4">
                            <div className="bg-muted/30 p-4 rounded-lg border border-muted">
                                <h4 className="text-xs font-bold uppercase text-muted-foreground mb-3">
                                    Migration SQL
                                </h4>
                                <p className="text-sm text-muted-foreground mb-4">
                                    To view the actual upgrade and downgrade SQL, inspect the migration file at the
                                    path shown above. The file contains <code className="bg-muted px-1 py-0.5 rounded">upgrade()</code> and{' '}
                                    <code className="bg-muted px-1 py-0.5 rounded">downgrade()</code> functions with the
                                    SQL operations.
                                </p>
                                <div className="bg-background p-3 rounded border">
                                    <p className="text-xs font-mono text-muted-foreground">
                                        # To view migration details via CLI:
                                        <br />
                                        $ alembic show {migration.revision}
                                    </p>
                                </div>
                            </div>
                        </div>

                        <Separator />

                        {/* CLI Documentation */}
                        <div className="bg-blue-50 dark:bg-blue-950/20 p-4 rounded-lg border border-blue-200 dark:border-blue-900">
                            <h4 className="text-sm font-bold text-blue-900 dark:text-blue-100 mb-2">
                                Migration Operations (CLI Only)
                            </h4>
                            <p className="text-sm text-blue-800 dark:text-blue-200 mb-3">
                                For production safety, migration operations must be performed via CLI:
                            </p>
                            <div className="space-y-2 text-xs font-mono bg-blue-100 dark:bg-blue-950/40 p-3 rounded">
                                <div># Apply migrations:</div>
                                <div className="text-blue-600 dark:text-blue-400">$ alembic upgrade head</div>
                                <div className="mt-2"># Rollback one migration:</div>
                                <div className="text-blue-600 dark:text-blue-400">$ alembic downgrade -1</div>
                                <div className="mt-2"># View migration history:</div>
                                <div className="text-blue-600 dark:text-blue-400">$ alembic history</div>
                            </div>
                        </div>
                    </div>
                </ScrollArea>
            </DialogContent>
        </Dialog>
    );
}
