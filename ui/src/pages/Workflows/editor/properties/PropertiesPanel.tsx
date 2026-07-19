/**
 * Right-rail properties: routes fields by selected node kind/type.
 */

import { useEffect, useRef } from 'react';
import type { Edge, Node } from '@xyflow/react';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';
import {
    isStepNodeData,
    isTriggerNode,
    isTriggerNodeData,
} from '../graphMapper';
import { TRIGGER_NODE_ID } from '../../workflowConstants';
import { getOutgoingTarget } from '../connectionRules';
import { WorkflowProperties } from './WorkflowProperties';
import { TriggerProperties } from './TriggerProperties';
import { ActionProperties } from './ActionProperties';
import { ConditionProperties } from './ConditionProperties';
import { WaitProperties } from './WaitProperties';
import { LoopProperties } from './LoopProperties';
import { ParallelProperties } from './ParallelProperties';
import { NextStepSelect, ConditionBranchSelects } from './OutgoingEdgeFields';
import type { WorkflowTriggerConfig, WorkflowStep } from '@/services/workflows.service';

export interface EditorMetaFields {
    name: string;
    description: string;
    enabled: boolean;
}

export interface PropertiesPanelProps {
    nodes: Node[];
    edges: Edge[];
    selectedNodeId: string | null;
    meta: EditorMetaFields;
    onMetaChange: <K extends keyof EditorMetaFields>(key: K, value: EditorMetaFields[K]) => void;
    onUpdateTrigger: (trigger: WorkflowTriggerConfig) => void;
    onUpdateStep: (nodeId: string, step: WorkflowStep) => void;
    onRenameStep: (nodeId: string, newName: string) => void;
    onDeleteNode: (nodeId: string) => void;
    /** Set or clear outgoing canvas edge for a source handle. */
    onSetOutgoing?: (
        sourceId: string,
        targetId: string | null,
        sourceHandle?: string | null,
    ) => void;
    className?: string;
}

export function PropertiesPanel({
    nodes,
    edges,
    selectedNodeId,
    meta,
    onMetaChange,
    onUpdateTrigger,
    onUpdateStep,
    onRenameStep,
    onDeleteNode,
    onSetOutgoing,
    className,
}: PropertiesPanelProps) {
    const panelRef = useRef<HTMLElement>(null);
    const prevSelectedRef = useRef<string | null>(null);

    const selected = selectedNodeId
        ? nodes.find((n) => n.id === selectedNodeId) ?? null
        : null;

    // Move focus into the panel when selection changes (palette add / issue click)
    useEffect(() => {
        if (selectedNodeId && selectedNodeId !== prevSelectedRef.current) {
            panelRef.current?.focus({ preventScroll: true });
        }
        prevSelectedRef.current = selectedNodeId;
    }, [selectedNodeId]);

    const stepNames = nodes
        .filter((n) => !isTriggerNode(n))
        .map((n) => n.id)
        .filter(Boolean);

    const otherStepNames = selected
        ? stepNames.filter((n) => n !== selected.id)
        : stepNames;

    const outgoing = selected
        ? edges.filter((e) => e.source === selected.id).map((e) => {
              const label = e.sourceHandle ? `${e.sourceHandle} → ` : '→ ';
              return `${label}${e.target}`;
          })
        : [];

    const isCondition =
        selected &&
        (selected.type === 'condition' ||
            (isStepNodeData(selected.data) && selected.data.step.type === 'condition'));

    let body: React.ReactNode;

    if (!selected) {
        body = (
            <WorkflowProperties meta={meta} onMetaChange={onMetaChange} stepCount={stepNames.length} />
        );
    } else if (isTriggerNode(selected) && isTriggerNodeData(selected.data)) {
        body = (
            <>
                <TriggerProperties
                    trigger={selected.data.trigger}
                    onChange={onUpdateTrigger}
                />
                {onSetOutgoing && (
                    <NextStepSelect
                        id="prop-trigger-next"
                        label="First step"
                        value={getOutgoingTarget(edges, selected.id)}
                        options={otherStepNames}
                        onChange={(t) => onSetOutgoing(selected.id, t)}
                        help="Which step runs after the trigger (same as drawing an edge)"
                    />
                )}
            </>
        );
    } else if (isStepNodeData(selected.data)) {
        const step = selected.data.step;
        const otherNames = stepNames.filter((n) => n !== selected.id);
        switch (step.type) {
            case 'action':
                body = (
                    <ActionProperties
                        key={selected.id}
                        step={step}
                        onChange={(s) => onUpdateStep(selected.id, s)}
                        onRename={(name) => onRenameStep(selected.id, name)}
                    />
                );
                break;
            case 'condition':
                body = (
                    <ConditionProperties
                        step={step}
                        onChange={(s) => onUpdateStep(selected.id, s)}
                        onRename={(name) => onRenameStep(selected.id, name)}
                    />
                );
                break;
            case 'wait_delay':
            case 'wait_condition':
            case 'wait_event':
                body = (
                    <WaitProperties
                        step={step}
                        onChange={(s) => onUpdateStep(selected.id, s)}
                        onRename={(name) => onRenameStep(selected.id, name)}
                    />
                );
                break;
            case 'loop':
                body = (
                    <LoopProperties
                        step={step}
                        otherStepNames={otherNames}
                        onChange={(s) => onUpdateStep(selected.id, s)}
                        onRename={(name) => onRenameStep(selected.id, name)}
                    />
                );
                break;
            case 'parallel':
                body = (
                    <ParallelProperties
                        step={step}
                        otherStepNames={otherNames}
                        onChange={(s) => onUpdateStep(selected.id, s)}
                        onRename={(name) => onRenameStep(selected.id, name)}
                    />
                );
                break;
            default:
                body = (
                    <ActionProperties
                        step={step}
                        onChange={(s) => onUpdateStep(selected.id, s)}
                        onRename={(name) => onRenameStep(selected.id, name)}
                    />
                );
        }

        // Outgoing edge controls (not for condition — uses dual branch selects below)
        if (onSetOutgoing && selected && !isCondition) {
            body = (
                <>
                    {body}
                    <NextStepSelect
                        value={getOutgoingTarget(edges, selected.id)}
                        options={otherNames}
                        onChange={(t) => onSetOutgoing(selected.id, t)}
                    />
                </>
            );
        } else if (onSetOutgoing && selected && isCondition) {
            body = (
                <>
                    {body}
                    <ConditionBranchSelects
                        trueValue={getOutgoingTarget(edges, selected.id, 'true')}
                        falseValue={getOutgoingTarget(edges, selected.id, 'false')}
                        options={otherNames}
                        onChangeTrue={(t) => onSetOutgoing(selected.id, t, 'true')}
                        onChangeFalse={(t) => onSetOutgoing(selected.id, t, 'false')}
                    />
                </>
            );
        }
    } else {
        body = <p className="text-xs text-muted-foreground">Unknown node</p>;
    }

    const canDelete = selected && selected.id !== TRIGGER_NODE_ID;
    const regionLabel = !selected
        ? 'Workflow properties'
        : isTriggerNode(selected)
          ? 'Trigger properties'
          : 'Step properties';

    return (
        <aside
            ref={panelRef}
            tabIndex={-1}
            role="region"
            aria-label={regionLabel}
            className={cn('flex flex-col h-full min-h-0 outline-none', className)}
            data-testid="workflow-editor-properties"
        >
            <div className="p-3 border-b shrink-0">
                <p className="text-sm font-medium">Properties</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                    {!selected
                        ? 'Workflow'
                        : isTriggerNode(selected)
                          ? 'Trigger'
                          : selected.id}
                </p>
            </div>

            <div className="flex-1 overflow-y-auto p-3 space-y-3">{body}</div>

            {selected && (
                <>
                    {outgoing.length > 0 && (
                        <div className="px-3 pb-2">
                            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-1">
                                Connected to
                            </p>
                            <ul className="text-xs font-mono space-y-0.5 text-muted-foreground">
                                {outgoing.map((line) => (
                                    <li key={line} className="truncate">
                                        {line}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                    <Separator />
                    <div className="p-3 shrink-0">
                        <Button
                            type="button"
                            variant="destructive"
                            size="sm"
                            className="w-full"
                            disabled={!canDelete}
                            onClick={() => canDelete && onDeleteNode(selected.id)}
                            data-testid="properties-delete-node"
                        >
                            {canDelete ? 'Delete step' : 'Trigger cannot be deleted'}
                        </Button>
                    </div>
                </>
            )}
        </aside>
    );
}

export default PropertiesPanel;
