import { memo } from 'react';
import type { Node, NodeProps } from '@xyflow/react';
import { Repeat } from 'lucide-react';
import { BaseStepNodeCard } from './BaseStepNode';
import { emitNodeDelete } from './nodeEvents';
import { isStepInvalid, stepBadge, stepSubtitle } from './nodeSummaries';
import type { StepNodeData } from '../graphMapper';

export type LoopFlowNode = Node<StepNodeData, 'loop'>;

function LoopNode({ id, data, selected }: NodeProps<LoopFlowNode>) {
    const step = data.step;
    return (
        <BaseStepNodeCard
            title={step.name || data.label || 'Loop'}
            subtitle={stepSubtitle(step)}
            badge={stepBadge(step)}
            accent="teal"
            icon={Repeat}
            selected={selected}
            invalid={isStepInvalid(step)}
            issueSeverity={data.issueSeverity ?? null}
            onDelete={() => emitNodeDelete(id)}
            testId="workflow-node-loop"
        />
    );
}

export default memo(LoopNode);
