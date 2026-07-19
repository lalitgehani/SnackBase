import { memo } from 'react';
import type { Node, NodeProps } from '@xyflow/react';
import { GitFork } from 'lucide-react';
import { BaseStepNodeCard } from './BaseStepNode';
import { emitNodeDelete } from './nodeEvents';
import { isStepInvalid, stepBadge, stepSubtitle } from './nodeSummaries';
import type { StepNodeData } from '../graphMapper';

export type ParallelFlowNode = Node<StepNodeData, 'parallel'>;

function ParallelNode({ id, data, selected }: NodeProps<ParallelFlowNode>) {
    const step = data.step;
    const locked = Boolean(data.locked);
    return (
        <BaseStepNodeCard
            title={step.name || data.label || 'Parallel'}
            subtitle={stepSubtitle(step)}
            badge={stepBadge(step)}
            accent="indigo"
            icon={GitFork}
            selected={selected}
            invalid={isStepInvalid(step)}
            issueSeverity={data.issueSeverity ?? null}
            runStatus={data.runStatus ?? null}
            locked={locked}
            onDelete={locked ? undefined : () => emitNodeDelete(id)}
            testId="workflow-node-parallel"
        />
    );
}

export default memo(ParallelNode);
