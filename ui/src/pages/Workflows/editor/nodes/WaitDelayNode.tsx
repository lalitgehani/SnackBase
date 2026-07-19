import { memo } from 'react';
import type { Node, NodeProps } from '@xyflow/react';
import { Timer } from 'lucide-react';
import { BaseStepNodeCard } from './BaseStepNode';
import { emitNodeDelete } from './nodeEvents';
import { isStepInvalid, stepBadge, stepSubtitle } from './nodeSummaries';
import type { StepNodeData } from '../graphMapper';

export type WaitDelayFlowNode = Node<StepNodeData, 'wait_delay'>;

function WaitDelayNode({ id, data, selected }: NodeProps<WaitDelayFlowNode>) {
    const step = data.step;
    return (
        <BaseStepNodeCard
            title={step.name || data.label || 'Wait delay'}
            subtitle={stepSubtitle(step)}
            badge={stepBadge(step)}
            accent="purple"
            icon={Timer}
            selected={selected}
            invalid={isStepInvalid(step)}
            issueSeverity={data.issueSeverity ?? null}
            onDelete={() => emitNodeDelete(id)}
            testId="workflow-node-wait_delay"
        />
    );
}

export default memo(WaitDelayNode);
