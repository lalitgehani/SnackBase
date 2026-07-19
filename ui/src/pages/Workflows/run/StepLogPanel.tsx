/**
 * Right rail for run detail: selected step log input/output/error.
 */

import type { Node } from '@xyflow/react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';
import {
    isStepNodeData,
    isTriggerNode,
    isTriggerNodeData,
    triggerSummary,
} from '../editor/graphMapper';
import type { WorkflowInstance, WorkflowStepLog } from '@/services/workflows.service';
import {
    formatWorkflowDate,
    InstanceStatusBadge,
    NodeRunStatusBadge,
} from '../InstanceStatusBadge';
import type { NodeRunStatus } from '../editor/runStatusMapper';
import { normalizeLogStatus } from '../editor/runStatusMapper';

function JsonBlock({ value, label }: { value: unknown; label: string }) {
    if (value == null) {
        return (
            <div className="space-y-1">
                <p className="text-xs font-medium text-muted-foreground">{label}</p>
                <p className="text-xs text-muted-foreground">—</p>
            </div>
        );
    }
    let text: string;
    try {
        text = JSON.stringify(value, null, 2);
    } catch {
        text = String(value);
    }
    return (
        <div className="space-y-1">
            <p className="text-xs font-medium text-muted-foreground">{label}</p>
            <pre className="text-[11px] font-mono bg-muted/60 rounded-md p-2 overflow-x-auto max-h-48 whitespace-pre-wrap break-all">
                {text}
            </pre>
        </div>
    );
}

export interface StepLogPanelProps {
    instance: WorkflowInstance;
    selectedNode: Node | null;
    stepLog: WorkflowStepLog | null;
    runStatus: NodeRunStatus | null;
    onCancel?: () => void;
    onResume?: () => void;
    cancelling?: boolean;
    resuming?: boolean;
    className?: string;
}

export function StepLogPanel({
    instance,
    selectedNode,
    stepLog,
    runStatus,
    onCancel,
    onResume,
    cancelling,
    resuming,
    className,
}: StepLogPanelProps) {
    const canCancel =
        instance.status === 'running' ||
        instance.status === 'waiting' ||
        instance.status === 'pending';
    const canResume = instance.status === 'failed' || instance.status === 'waiting';

    return (
        <aside
            className={cn(
                'w-80 shrink-0 border-l bg-card overflow-y-auto p-4 space-y-4',
                className,
            )}
            data-testid="step-log-panel"
        >
            <div className="space-y-2">
                <div className="flex items-center justify-between gap-2">
                    <h3 className="text-sm font-semibold">Run</h3>
                    <InstanceStatusBadge status={instance.status} />
                </div>
                <p className="text-xs text-muted-foreground font-mono truncate" title={instance.id}>
                    {instance.id}
                </p>
                {instance.current_step && (
                    <p className="text-xs text-muted-foreground">
                        Current step:{' '}
                        <code className="bg-muted px-1 rounded">{instance.current_step}</code>
                    </p>
                )}
                {instance.error_message && (
                    <p className="text-xs text-destructive whitespace-pre-wrap" data-testid="instance-error">
                        {instance.error_message}
                    </p>
                )}
                <div className="flex flex-wrap gap-2 pt-1">
                    {canCancel && onCancel && (
                        <Button
                            variant="outline"
                            size="sm"
                            className="h-7 text-xs"
                            disabled={cancelling}
                            onClick={onCancel}
                            data-testid="run-cancel-btn"
                        >
                            {cancelling ? 'Cancelling…' : 'Cancel'}
                        </Button>
                    )}
                    {canResume && onResume && (
                        <Button
                            variant="outline"
                            size="sm"
                            className="h-7 text-xs"
                            disabled={resuming}
                            onClick={onResume}
                            data-testid="run-resume-btn"
                        >
                            {resuming ? 'Resuming…' : 'Resume'}
                        </Button>
                    )}
                </div>
            </div>

            <Separator />

            {!selectedNode && (
                <p className="text-sm text-muted-foreground">
                    Select a node on the graph to inspect its step log.
                </p>
            )}

            {selectedNode && isTriggerNode(selectedNode) && isTriggerNodeData(selectedNode.data) && (
                <div className="space-y-2">
                    <h4 className="text-sm font-medium">Trigger</h4>
                    <p className="text-xs text-muted-foreground">
                        {triggerSummary(selectedNode.data.trigger)}
                    </p>
                    {runStatus && <NodeRunStatusBadge status={runStatus} />}
                </div>
            )}

            {selectedNode && isStepNodeData(selectedNode.data) && (
                <div className="space-y-3" data-testid="step-log-detail">
                    <div>
                        <h4 className="text-sm font-medium truncate">
                            {selectedNode.data.step.name}
                        </h4>
                        <div className="flex items-center gap-2 mt-1 flex-wrap">
                            <Badge variant="secondary" className="text-xs">
                                {selectedNode.data.step.type}
                            </Badge>
                            {(runStatus || stepLog) && (
                                <NodeRunStatusBadge
                                    status={
                                        runStatus ??
                                        normalizeLogStatus(stepLog!.status)
                                    }
                                />
                            )}
                        </div>
                    </div>

                    {!stepLog && (
                        <p className="text-sm text-muted-foreground" data-testid="step-not-executed">
                            Not executed yet (no step log).
                        </p>
                    )}

                    {stepLog && (
                        <>
                            <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                                <div>
                                    <span className="font-medium text-foreground">Started</span>
                                    <p>{formatWorkflowDate(stepLog.started_at)}</p>
                                </div>
                                <div>
                                    <span className="font-medium text-foreground">Completed</span>
                                    <p>{formatWorkflowDate(stepLog.completed_at)}</p>
                                </div>
                            </div>
                            {stepLog.error_message && (
                                <div
                                    className="rounded-md border border-destructive/40 bg-destructive/5 p-2"
                                    data-testid="step-log-error"
                                >
                                    <p className="text-xs font-medium text-destructive mb-1">
                                        Error
                                    </p>
                                    <p className="text-xs text-destructive whitespace-pre-wrap">
                                        {stepLog.error_message}
                                    </p>
                                </div>
                            )}
                            <JsonBlock label="Input" value={stepLog.input} />
                            <JsonBlock label="Output" value={stepLog.output} />
                        </>
                    )}
                </div>
            )}
        </aside>
    );
}
