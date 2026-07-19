import { memo } from 'react';
import type { Node, NodeProps } from '@xyflow/react';
import { Play } from 'lucide-react';
import { BaseStepNodeCard } from './BaseStepNode';
import { emitNodeDelete } from './nodeEvents';
import { isStepInvalid, stepBadge, stepSubtitle } from './nodeSummaries';
import type { StepNodeData } from '../graphMapper';

export type ActionFlowNode = Node<StepNodeData, 'action'>;

function ActionNode({ id, data, selected }: NodeProps<ActionFlowNode>) {
    const step = data.step;
    return (
        <BaseStepNodeCard
            title={step.name || data.label || 'Action'}
            subtitle={stepSubtitle(step)}
            badge={stepBadge(step)}
            accent="blue"
            icon={Play}
            selected={selected}
            invalid={isStepInvalid(step)}
            onDelete={() => emitNodeDelete(id)}
            testId="workflow-node-action"
        />
    );
}

export default memo(ActionNode);
