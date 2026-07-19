import { memo } from 'react';
import type { Node, NodeProps } from '@xyflow/react';
import { Radio } from 'lucide-react';
import { BaseStepNodeCard } from './BaseStepNode';
import { emitNodeDelete } from './nodeEvents';
import { isStepInvalid, stepBadge, stepSubtitle } from './nodeSummaries';
import type { StepNodeData } from '../graphMapper';

export type WaitEventFlowNode = Node<StepNodeData, 'wait_event'>;

function WaitEventNode({ id, data, selected }: NodeProps<WaitEventFlowNode>) {
    const step = data.step;
    return (
        <BaseStepNodeCard
            title={step.name || data.label || 'Wait event'}
            subtitle={stepSubtitle(step)}
            badge={stepBadge(step)}
            accent="purple"
            icon={Radio}
            selected={selected}
            invalid={isStepInvalid(step)}
            onDelete={() => emitNodeDelete(id)}
            testId="workflow-node-wait_event"
        />
    );
}

export default memo(WaitEventNode);
