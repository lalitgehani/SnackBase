import type { NodeTypes } from '@xyflow/react';
import TriggerNode from './TriggerNode';
import ActionNode from './ActionNode';
import ConditionNode from './ConditionNode';
import WaitDelayNode from './WaitDelayNode';
import WaitConditionNode from './WaitConditionNode';
import WaitEventNode from './WaitEventNode';
import LoopNode from './LoopNode';
import ParallelNode from './ParallelNode';

export const workflowNodeTypes: NodeTypes = {
    trigger: TriggerNode,
    action: ActionNode,
    condition: ConditionNode,
    wait_delay: WaitDelayNode,
    wait_condition: WaitConditionNode,
    wait_event: WaitEventNode,
    loop: LoopNode,
    parallel: ParallelNode,
};

export {
    TriggerNode,
    ActionNode,
    ConditionNode,
    WaitDelayNode,
    WaitConditionNode,
    WaitEventNode,
    LoopNode,
    ParallelNode,
};
