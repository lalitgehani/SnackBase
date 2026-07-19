/**
 * Shared status badges for workflow instances and step logs.
 */

import type { WorkflowInstance } from '@/services/workflows.service';
import type { NodeRunStatus } from './editor/runStatusMapper';
import { cn } from '@/lib/utils';

type InstanceStatus = WorkflowInstance['status'];

const INSTANCE_STATUS_CLASS: Record<InstanceStatus, string> = {
    pending: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
    running: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
    waiting: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
    completed: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
    failed: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
    cancelled: 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400',
};

const NODE_RUN_STATUS_CLASS: Record<NodeRunStatus, string> = {
    pending: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
    running: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
    waiting: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
    completed: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
    failed: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
    skipped: 'bg-muted text-muted-foreground',
};

export function InstanceStatusBadge({
    status,
    className,
}: {
    status: InstanceStatus | string;
    className?: string;
}) {
    const cls =
        INSTANCE_STATUS_CLASS[status as InstanceStatus] ??
        'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300';
    return (
        <span
            className={cn(
                'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium capitalize',
                cls,
                className,
            )}
            data-testid="instance-status-badge"
        >
            {status}
        </span>
    );
}

export function NodeRunStatusBadge({
    status,
    className,
}: {
    status: NodeRunStatus | string;
    className?: string;
}) {
    const cls =
        NODE_RUN_STATUS_CLASS[status as NodeRunStatus] ??
        'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300';
    return (
        <span
            className={cn(
                'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium capitalize',
                cls,
                className,
            )}
            data-testid="node-run-status-badge"
        >
            {status}
        </span>
    );
}

export function formatWorkflowDate(dateStr: string | null | undefined): string {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleString();
}
