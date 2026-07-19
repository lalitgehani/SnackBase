import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@/test/utils';
import { WorkflowCanvas } from '../WorkflowCanvas';

// React Flow uses ResizeObserver and measurement APIs not fully available in jsdom
class ResizeObserverMock {
    observe() {}
    unobserve() {}
    disconnect() {}
}
vi.stubGlobal('ResizeObserver', ResizeObserverMock);

describe('WorkflowCanvas', () => {
    it('mounts React Flow shell with canvas container', () => {
        render(
            <div style={{ width: 800, height: 600 }}>
                <WorkflowCanvas
                    nodes={[]}
                    edges={[]}
                    onNodesChange={() => {}}
                    onEdgesChange={() => {}}
                />
            </div>,
        );

        expect(screen.getByTestId('workflow-canvas')).toBeInTheDocument();
    });

    it('read-only locked nodes hide delete control', () => {
        render(
            <div style={{ width: 800, height: 600 }}>
                <WorkflowCanvas
                    nodes={[
                        {
                            id: 'step_a',
                            type: 'action',
                            position: { x: 0, y: 0 },
                            draggable: false,
                            data: {
                                kind: 'step',
                                label: 'step_a',
                                locked: true,
                                step: {
                                    type: 'action',
                                    name: 'step_a',
                                    action_type: 'send_webhook',
                                    config: {},
                                },
                            },
                        },
                    ]}
                    edges={[]}
                    onNodesChange={() => {}}
                    onEdgesChange={() => {}}
                    readOnly
                    showToolbar={false}
                />
            </div>,
        );

        expect(screen.getByTestId('workflow-node-action')).toBeInTheDocument();
        expect(screen.queryByTestId('workflow-node-delete')).not.toBeInTheDocument();
    });

    it('applies failed run status badge on node', () => {
        render(
            <div style={{ width: 800, height: 600 }}>
                <WorkflowCanvas
                    nodes={[
                        {
                            id: 'step_a',
                            type: 'action',
                            position: { x: 0, y: 0 },
                            data: {
                                kind: 'step',
                                label: 'step_a',
                                locked: true,
                                runStatus: 'failed',
                                step: {
                                    type: 'action',
                                    name: 'step_a',
                                    action_type: 'send_webhook',
                                    config: {},
                                },
                            },
                        },
                    ]}
                    edges={[]}
                    onNodesChange={() => {}}
                    onEdgesChange={() => {}}
                    readOnly
                    showToolbar={false}
                />
            </div>,
        );

        const node = screen.getByTestId('workflow-node-action');
        expect(node).toHaveAttribute('data-run-status', 'failed');
        expect(screen.getByTestId('workflow-node-run-status')).toHaveTextContent('failed');
    });

    it('renders action card nodes when provided', () => {
        render(
            <div style={{ width: 800, height: 600 }}>
                <WorkflowCanvas
                    nodes={[
                        {
                            id: 'step_a',
                            type: 'action',
                            position: { x: 0, y: 0 },
                            data: {
                                kind: 'step',
                                label: 'step_a',
                                step: {
                                    type: 'action',
                                    name: 'step_a',
                                    action_type: 'send_webhook',
                                    config: {},
                                },
                            },
                        },
                    ]}
                    edges={[]}
                    onNodesChange={() => {}}
                    onEdgesChange={() => {}}
                />
            </div>,
        );

        expect(screen.getByTestId('workflow-canvas')).toBeInTheDocument();
        expect(screen.getByTestId('workflow-node-action')).toBeInTheDocument();
        expect(screen.getByText('step_a')).toBeInTheDocument();
    });

    it('renders condition with dual handles', () => {
        render(
            <div style={{ width: 800, height: 600 }}>
                <WorkflowCanvas
                    nodes={[
                        {
                            id: 'check',
                            type: 'condition',
                            position: { x: 0, y: 0 },
                            data: {
                                kind: 'step',
                                label: 'check',
                                step: {
                                    type: 'condition',
                                    name: 'check',
                                    expression: 'x > 1',
                                },
                            },
                        },
                    ]}
                    edges={[]}
                    onNodesChange={() => {}}
                    onEdgesChange={() => {}}
                />
            </div>,
        );

        expect(screen.getByTestId('workflow-node-condition')).toBeInTheDocument();
        expect(screen.getByTestId('condition-handle-true')).toBeInTheDocument();
        expect(screen.getByTestId('condition-handle-false')).toBeInTheDocument();
    });
});
