import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { Edge, Node } from '@xyflow/react';
import { PropertiesPanel } from '../properties/PropertiesPanel';
import { TRIGGER_NODE_ID } from '../../workflowConstants';

const meta = { name: 'WF', description: '', enabled: true };

function triggerNode(): Node {
    return {
        id: TRIGGER_NODE_ID,
        type: 'trigger',
        position: { x: 0, y: 0 },
        data: { kind: 'trigger', label: 'Trigger', trigger: { type: 'manual' } },
    };
}

function actionNode(id: string): Node {
    return {
        id,
        type: 'action',
        position: { x: 100, y: 0 },
        data: {
            kind: 'step',
            label: id,
            step: {
                type: 'action',
                name: id,
                action_type: 'send_webhook',
                config: { url: 'https://x' },
            },
        },
    };
}

function conditionNode(id: string): Node {
    return {
        id,
        type: 'condition',
        position: { x: 100, y: 0 },
        data: {
            kind: 'step',
            label: id,
            step: { type: 'condition', name: id, expression: 'true' },
        },
    };
}

describe('PropertiesPanel', () => {
    it('shows workflow properties when nothing selected', () => {
        render(
            <PropertiesPanel
                nodes={[triggerNode()]}
                edges={[]}
                selectedNodeId={null}
                meta={meta}
                onMetaChange={vi.fn()}
                onUpdateTrigger={vi.fn()}
                onUpdateStep={vi.fn()}
                onRenameStep={vi.fn()}
                onDeleteNode={vi.fn()}
            />,
        );
        expect(screen.getByTestId('properties-workflow')).toBeInTheDocument();
        expect(screen.getByTestId('workflow-editor-properties')).toHaveAttribute(
            'aria-label',
            'Workflow properties',
        );
    });

    it('renders action properties and next-step select', () => {
        const onSetOutgoing = vi.fn();
        const nodes = [triggerNode(), actionNode('a'), actionNode('b')];
        const edges: Edge[] = [{ id: 'a->b', source: 'a', target: 'b' }];
        render(
            <PropertiesPanel
                nodes={nodes}
                edges={edges}
                selectedNodeId="a"
                meta={meta}
                onMetaChange={vi.fn()}
                onUpdateTrigger={vi.fn()}
                onUpdateStep={vi.fn()}
                onRenameStep={vi.fn()}
                onDeleteNode={vi.fn()}
                onSetOutgoing={onSetOutgoing}
            />,
        );
        expect(screen.getByTestId('properties-action')).toBeInTheDocument();
        expect(screen.getByTestId('properties-step-name')).toBeInTheDocument();
        expect(screen.getByTestId('prop-next-step')).toBeInTheDocument();
        expect(screen.getByTestId('workflow-editor-properties')).toHaveAttribute(
            'aria-label',
            'Step properties',
        );
    });

    it('renders condition branch selects', () => {
        const nodes = [triggerNode(), conditionNode('gate'), actionNode('yes'), actionNode('no')];
        render(
            <PropertiesPanel
                nodes={nodes}
                edges={[]}
                selectedNodeId="gate"
                meta={meta}
                onMetaChange={vi.fn()}
                onUpdateTrigger={vi.fn()}
                onUpdateStep={vi.fn()}
                onRenameStep={vi.fn()}
                onDeleteNode={vi.fn()}
                onSetOutgoing={vi.fn()}
            />,
        );
        expect(screen.getByTestId('properties-condition')).toBeInTheDocument();
        expect(screen.getByTestId('prop-on-true')).toBeInTheDocument();
        expect(screen.getByTestId('prop-on-false')).toBeInTheDocument();
    });

    it('calls onDeleteNode when delete is clicked', async () => {
        const user = userEvent.setup();
        const onDeleteNode = vi.fn();
        render(
            <PropertiesPanel
                nodes={[triggerNode(), actionNode('a')]}
                edges={[]}
                selectedNodeId="a"
                meta={meta}
                onMetaChange={vi.fn()}
                onUpdateTrigger={vi.fn()}
                onUpdateStep={vi.fn()}
                onRenameStep={vi.fn()}
                onDeleteNode={onDeleteNode}
            />,
        );
        await user.click(screen.getByTestId('properties-delete-node'));
        expect(onDeleteNode).toHaveBeenCalledWith('a');
    });

    it('shows first-step select for trigger', () => {
        render(
            <PropertiesPanel
                nodes={[triggerNode(), actionNode('a')]}
                edges={[]}
                selectedNodeId={TRIGGER_NODE_ID}
                meta={meta}
                onMetaChange={vi.fn()}
                onUpdateTrigger={vi.fn()}
                onUpdateStep={vi.fn()}
                onRenameStep={vi.fn()}
                onDeleteNode={vi.fn()}
                onSetOutgoing={vi.fn()}
            />,
        );
        expect(screen.getByTestId('properties-trigger')).toBeInTheDocument();
        expect(screen.getByTestId('prop-trigger-next')).toBeInTheDocument();
    });
});
