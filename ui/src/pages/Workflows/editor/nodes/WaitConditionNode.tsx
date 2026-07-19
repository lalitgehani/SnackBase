import { memo } from 'react';
import type { Node, NodeProps } from '@xyflow/react';
import { Hourglass } from 'lucide-react';
import { BaseStepNodeCard } from './BaseStepNode';
import { emitNodeDelete } from './nodeEvents';
import { isStepInvalid, stepBadge, stepSubtitle } from './nodeSummaries';
import type { StepNodeData } from '../graphMapper';

export type WaitConditionFlowNode = Node<StepNodeData, 'wait_condition'>;

function WaitConditionNode({ id, data, selected }: NodeProps<WaitConditionFlowNode>) {
    const step = data.step;
    return (
        <BaseStepNodeCard
            title={step.name || data.label || 'Wait condition'}
            subtitle={stepSubtitle(step)}
            badge={stepBadge(step)}
            accent="purple"
            icon={Hourglass}
            selected={selected}
            invalid={isStepInvalid(step)}
            onDelete={() => emitNodeDelete(id)}
            testId="workflow-node-wait_condition"
        />
    );
}

export default memo(WaitConditionNode);
