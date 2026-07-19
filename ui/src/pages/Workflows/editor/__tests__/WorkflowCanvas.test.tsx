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

    it('renders nodes when provided', () => {
        render(
            <div style={{ width: 800, height: 600 }}>
                <WorkflowCanvas
                    nodes={[
                        {
                            id: 'step_a',
                            position: { x: 0, y: 0 },
                            data: { label: 'step_a' },
                        },
                    ]}
                    edges={[]}
                    onNodesChange={() => {}}
                    onEdgesChange={() => {}}
                />
            </div>,
        );

        expect(screen.getByTestId('workflow-canvas')).toBeInTheDocument();
        // RF renders node labels in the DOM
        expect(screen.getByText('step_a')).toBeInTheDocument();
    });
});
