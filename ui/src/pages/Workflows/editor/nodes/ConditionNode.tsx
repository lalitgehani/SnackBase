import { memo } from 'react';
import { Handle, Position, type Node, type NodeProps } from '@xyflow/react';
import { GitBranch } from 'lucide-react';
import { BaseStepNodeCard } from './BaseStepNode';
import { emitNodeDelete } from './nodeEvents';
import { isStepInvalid, stepBadge, stepSubtitle } from './nodeSummaries';
import type { StepNodeData } from '../graphMapper';

export type ConditionFlowNode = Node<StepNodeData, 'condition'>;

function ConditionNode({ id, data, selected }: NodeProps<ConditionFlowNode>) {
    const step = data.step;
    const locked = Boolean(data.locked);
    return (
        <BaseStepNodeCard
            title={step.name || data.label || 'Condition'}
            subtitle={stepSubtitle(step)}
            badge={stepBadge(step)}
            accent="amber"
            icon={GitBranch}
            selected={selected}
            showSourceHandle={false}
            invalid={isStepInvalid(step)}
            issueSeverity={data.issueSeverity ?? null}
            runStatus={data.runStatus ?? null}
            locked={locked}
            onDelete={locked ? undefined : () => emitNodeDelete(id)}
            testId="workflow-node-condition"
            customSourceHandles={
                <>
                    <Handle
                        type="source"
                        position={Position.Right}
                        id="true"
                        style={{ top: '35%' }}
                        className="!h-2.5 !w-2.5 !border-2 !border-background !bg-green-600"
                        data-testid="condition-handle-true"
                        aria-label="True branch"
                    />
                    <Handle
                        type="source"
                        position={Position.Right}
                        id="false"
                        style={{ top: '70%' }}
                        className="!h-2.5 !w-2.5 !border-2 !border-background !bg-red-500"
                        data-testid="condition-handle-false"
                        aria-label="False branch"
                    />
                    <div className="absolute right-2 top-[28%] text-[9px] font-medium text-green-700 dark:text-green-400 pointer-events-none">
                        T
                    </div>
                    <div className="absolute right-2 top-[63%] text-[9px] font-medium text-red-600 dark:text-red-400 pointer-events-none">
                        F
                    </div>
                </>
            }
        />
    );
}

export default memo(ConditionNode);
