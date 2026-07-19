import { memo } from 'react';
import type { Node, NodeProps } from '@xyflow/react';
import { Zap } from 'lucide-react';
import { BaseStepNodeCard } from './BaseStepNode';
import { triggerSubtitle } from './nodeSummaries';
import type { TriggerNodeData } from '../graphMapper';

export type TriggerFlowNode = Node<TriggerNodeData, 'trigger'>;

function TriggerNode({ data, selected }: NodeProps<TriggerFlowNode>) {
    const trigger = data.trigger;
    return (
        <BaseStepNodeCard
            title="Trigger"
            subtitle={triggerSubtitle(trigger)}
            badge={trigger?.type ?? 'manual'}
            accent="slate"
            icon={Zap}
            selected={selected}
            showTargetHandle={false}
            showSourceHandle={true}
            locked
            issueSeverity={data.issueSeverity ?? null}
            testId="workflow-node-trigger"
        />
    );
}

export default memo(TriggerNode);
