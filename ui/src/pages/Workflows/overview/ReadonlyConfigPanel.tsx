/**
 * Read-only right rail: workflow / trigger / step config summary.
 */

import type { ReactNode } from 'react';
import type { Node } from '@xyflow/react';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';
import {
    isStepNodeData,
    isTriggerNode,
    isTriggerNodeData,
    triggerSummary,
} from '../editor/graphMapper';
import { stepBadge, stepSubtitle } from '../editor/nodes/nodeSummaries';
import type { Workflow } from '@/services/workflows.service';

export interface ReadonlyConfigPanelProps {
    workflow: Workflow;
    selectedNode: Node | null;
    className?: string;
}

function Field({ label, children }: { label: string; children: ReactNode }) {
    return (
        <div className="space-y-1">
            <p className="text-xs font-medium text-muted-foreground">{label}</p>
            <div className="text-sm break-words">{children}</div>
        </div>
    );
}

export function ReadonlyConfigPanel({
    workflow,
    selectedNode,
    className,
}: ReadonlyConfigPanelProps) {
    if (!selectedNode) {
        return (
            <aside
                className={cn(
                    'w-72 shrink-0 border-l bg-card overflow-y-auto p-4 space-y-4',
                    className,
                )}
                data-testid="readonly-config-panel"
            >
                <div>
                    <h3 className="text-sm font-semibold">Workflow</h3>
                    <p className="text-xs text-muted-foreground mt-1">
                        Select a node to inspect its configuration.
                    </p>
                </div>
                <Separator />
                <Field label="Name">{workflow.name}</Field>
                {workflow.description && (
                    <Field label="Description">{workflow.description}</Field>
                )}
                <Field label="Status">
                    <Badge variant={workflow.enabled ? 'default' : 'secondary'}>
                        {workflow.enabled ? 'Enabled' : 'Disabled'}
                    </Badge>
                </Field>
                <Field label="Trigger">{triggerSummary(workflow.trigger_config)}</Field>
                <Field label="Steps">{workflow.steps.length}</Field>
            </aside>
        );
    }

    if (isTriggerNode(selectedNode) && isTriggerNodeData(selectedNode.data)) {
        const t = selectedNode.data.trigger;
        return (
            <aside
                className={cn(
                    'w-72 shrink-0 border-l bg-card overflow-y-auto p-4 space-y-4',
                    className,
                )}
                data-testid="readonly-config-panel"
            >
                <div>
                    <h3 className="text-sm font-semibold">Trigger</h3>
                    <p className="text-xs text-muted-foreground mt-1">
                        {triggerSummary(t)}
                    </p>
                </div>
                <Separator />
                <Field label="Type">
                    <Badge variant="outline" className="capitalize">
                        {t.type}
                    </Badge>
                </Field>
                {t.type === 'event' && (
                    <>
                        <Field label="Event">
                            <code className="text-xs bg-muted px-1.5 py-0.5 rounded">
                                {t.event}
                            </code>
                        </Field>
                        {t.collection && <Field label="Collection">{t.collection}</Field>}
                        {t.condition && (
                            <Field label="Condition">
                                <code className="text-xs font-mono block whitespace-pre-wrap">
                                    {t.condition}
                                </code>
                            </Field>
                        )}
                    </>
                )}
                {t.type === 'schedule' && (
                    <Field label="Cron">
                        <code className="text-xs bg-muted px-1.5 py-0.5 rounded">{t.cron}</code>
                    </Field>
                )}
                {t.type === 'webhook' && t.token && (
                    <Field label="Webhook path">
                        <code className="text-xs bg-muted px-1.5 py-0.5 rounded break-all">
                            /api/v1/workflow-webhooks/{t.token}
                        </code>
                    </Field>
                )}
            </aside>
        );
    }

    if (isStepNodeData(selectedNode.data)) {
        const step = selectedNode.data.step;
        return (
            <aside
                className={cn(
                    'w-72 shrink-0 border-l bg-card overflow-y-auto p-4 space-y-4',
                    className,
                )}
                data-testid="readonly-config-panel"
            >
                <div>
                    <h3 className="text-sm font-semibold truncate">{step.name}</h3>
                    <p className="text-xs text-muted-foreground mt-1">
                        {stepSubtitle(step)}
                    </p>
                </div>
                <Separator />
                <Field label="Type">
                    <Badge variant="secondary" className="text-xs">
                        {stepBadge(step) ?? step.type}
                    </Badge>
                </Field>
                {step.type === 'action' && step.action_type != null && (
                    <Field label="Action type">
                        <code className="text-xs">{String(step.action_type)}</code>
                    </Field>
                )}
                {step.type === 'condition' && step.expression != null && (
                    <Field label="Expression">
                        <code className="text-xs font-mono block whitespace-pre-wrap">
                            {String(step.expression)}
                        </code>
                    </Field>
                )}
                {(step.type === 'wait_condition' || step.type === 'wait_event') && (
                    <>
                        {step.expression != null && (
                            <Field label="Expression">
                                <code className="text-xs font-mono block whitespace-pre-wrap">
                                    {String(step.expression)}
                                </code>
                            </Field>
                        )}
                        {step.event != null && (
                            <Field label="Event">
                                <code className="text-xs">{String(step.event)}</code>
                            </Field>
                        )}
                    </>
                )}
                {step.type === 'wait_delay' && step.duration != null && (
                    <Field label="Duration">{String(step.duration)}</Field>
                )}
                {step.type === 'loop' && step.items != null && (
                    <Field label="Items">
                        <code className="text-xs font-mono block whitespace-pre-wrap">
                            {String(step.items)}
                        </code>
                    </Field>
                )}
                {step.type === 'parallel' && Array.isArray(step.branches) && (
                    <Field label="Branches">
                        <ul className="list-disc list-inside text-xs space-y-0.5">
                            {(step.branches as unknown[]).map((b, i) => (
                                <li key={i}>
                                    <code>{String(b)}</code>
                                </li>
                            ))}
                        </ul>
                    </Field>
                )}
                {step.next != null && step.next !== '' && (
                    <Field label="Next">
                        <code className="text-xs font-mono">{String(step.next)}</code>
                    </Field>
                )}
                {step.on_true != null && (
                    <Field label="On true">
                        <code className="text-xs font-mono">{String(step.on_true)}</code>
                    </Field>
                )}
                {step.on_false != null && (
                    <Field label="On false">
                        <code className="text-xs font-mono">{String(step.on_false)}</code>
                    </Field>
                )}
            </aside>
        );
    }

    return (
        <aside
            className={cn('w-72 shrink-0 border-l bg-card p-4', className)}
            data-testid="readonly-config-panel"
        >
            <p className="text-sm text-muted-foreground">Unknown node.</p>
        </aside>
    );
}
