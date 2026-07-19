/**
 * Shared card chrome for workflow canvas nodes.
 */

import { memo, type ReactNode } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { X, AlertCircle, AlertTriangle, type LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { NodeRunStatus } from '../graphMapper';

export type NodeAccent =
    | 'slate'
    | 'blue'
    | 'amber'
    | 'purple'
    | 'teal'
    | 'indigo';

const ACCENT_BAR: Record<NodeAccent, string> = {
    slate: 'bg-slate-500',
    blue: 'bg-blue-500',
    amber: 'bg-amber-500',
    purple: 'bg-purple-500',
    teal: 'bg-teal-500',
    indigo: 'bg-indigo-500',
};

const ACCENT_ICON: Record<NodeAccent, string> = {
    slate: 'text-slate-600 dark:text-slate-300',
    blue: 'text-blue-600 dark:text-blue-400',
    amber: 'text-amber-600 dark:text-amber-400',
    purple: 'text-purple-600 dark:text-purple-400',
    teal: 'text-teal-600 dark:text-teal-400',
    indigo: 'text-indigo-600 dark:text-indigo-400',
};

const RUN_STATUS_BORDER: Record<NodeRunStatus, string> = {
    pending: 'border-muted-foreground/30 opacity-80',
    running: 'border-blue-500 ring-2 ring-blue-500/40 shadow-sm',
    waiting: 'border-amber-500 ring-2 ring-amber-500/30',
    completed: 'border-green-500/70',
    failed: 'border-destructive ring-2 ring-destructive/30',
    skipped: 'border-dashed border-muted-foreground/40 opacity-70',
};

const RUN_STATUS_BADGE: Record<NodeRunStatus, string> = {
    pending: 'bg-muted text-muted-foreground',
    running: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
    waiting: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200',
    completed: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
    failed: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
    skipped: 'bg-muted text-muted-foreground',
};

export interface BaseStepNodeProps {
    title: string;
    subtitle?: string;
    badge?: string;
    accent: NodeAccent;
    icon: LucideIcon;
    selected?: boolean;
    showTargetHandle?: boolean;
    showSourceHandle?: boolean;
    /** When true, no delete control. */
    locked?: boolean;
    /** Field or graph validation: error shows red icon, warning amber. */
    invalid?: boolean;
    issueSeverity?: 'error' | 'warning' | null;
    /** Runtime status overlay (run detail). */
    runStatus?: NodeRunStatus | null;
    onDelete?: () => void;
    /** Extra content below subtitle (e.g. condition handles area). */
    children?: ReactNode;
    /** Custom source handles (condition). When set, default source handle is omitted. */
    customSourceHandles?: ReactNode;
    className?: string;
    testId?: string;
}

export function BaseStepNodeCard({
    title,
    subtitle,
    badge,
    accent,
    icon: Icon,
    selected,
    showTargetHandle = true,
    showSourceHandle = true,
    locked = false,
    invalid = false,
    issueSeverity = null,
    runStatus = null,
    onDelete,
    children,
    customSourceHandles,
    className,
    testId,
}: BaseStepNodeProps) {
    const severity: 'error' | 'warning' | null =
        issueSeverity ?? (invalid ? 'error' : null);

    return (
        <div
            className={cn(
                'relative min-w-[180px] max-w-[240px] rounded-lg border bg-card text-card-foreground shadow-sm group',
                selected && 'ring-2 ring-primary border-primary',
                !runStatus && severity === 'error' && !selected && 'border-destructive/50',
                !runStatus && severity === 'warning' && !selected && 'border-amber-500/50',
                runStatus && !selected && RUN_STATUS_BORDER[runStatus],
                className,
            )}
            data-testid={testId}
            data-run-status={runStatus ?? undefined}
        >
            <div className={cn('absolute left-0 top-0 bottom-0 w-1 rounded-l-lg', ACCENT_BAR[accent])} />

            {showTargetHandle && (
                <Handle
                    type="target"
                    position={Position.Left}
                    className="!h-2.5 !w-2.5 !border-2 !border-background !bg-muted-foreground"
                    aria-label="Input"
                />
            )}

            <div className="pl-3 pr-2 py-2.5 flex flex-col gap-1">
                <div className="flex items-start gap-2">
                    <Icon className={cn('h-4 w-4 shrink-0 mt-0.5', ACCENT_ICON[accent])} />
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5 flex-wrap">
                            <p className="text-sm font-medium truncate leading-tight">{title || 'Unnamed'}</p>
                            {runStatus && (
                                <span
                                    className={cn(
                                        'inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium capitalize',
                                        RUN_STATUS_BADGE[runStatus],
                                    )}
                                    data-testid="workflow-node-run-status"
                                >
                                    {runStatus}
                                </span>
                            )}
                            {!runStatus && severity === 'error' && (
                                <AlertCircle
                                    className="h-3.5 w-3.5 text-destructive shrink-0"
                                    aria-label="Validation error"
                                />
                            )}
                            {!runStatus && severity === 'warning' && (
                                <AlertTriangle
                                    className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400 shrink-0"
                                    aria-label="Validation warning"
                                />
                            )}
                            {runStatus === 'failed' && (
                                <AlertCircle
                                    className="h-3.5 w-3.5 text-destructive shrink-0"
                                    aria-label="Step failed"
                                />
                            )}
                        </div>
                        {badge && (
                            <span className="inline-block mt-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                                {badge}
                            </span>
                        )}
                        {subtitle && (
                            <p className="text-xs text-muted-foreground truncate mt-0.5" title={subtitle}>
                                {subtitle}
                            </p>
                        )}
                    </div>
                    {!locked && onDelete && (
                        <button
                            type="button"
                            className="opacity-0 group-hover:opacity-100 focus:opacity-100 h-6 w-6 flex items-center justify-center rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive shrink-0 transition-opacity"
                            onClick={(e) => {
                                e.stopPropagation();
                                onDelete();
                            }}
                            aria-label="Delete step"
                            data-testid="workflow-node-delete"
                        >
                            <X className="h-3.5 w-3.5" />
                        </button>
                    )}
                </div>
                {children}
            </div>

            {customSourceHandles}
            {!customSourceHandles && showSourceHandle && (
                <Handle
                    type="source"
                    position={Position.Right}
                    className="!h-2.5 !w-2.5 !border-2 !border-background !bg-muted-foreground"
                    aria-label="Output"
                />
            )}
        </div>
    );
}

export type { NodeProps };

export default memo(BaseStepNodeCard);
