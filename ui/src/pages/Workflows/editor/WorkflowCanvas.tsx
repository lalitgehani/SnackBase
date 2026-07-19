/**
 * React Flow host for the workflow visual editor.
 * Phase 1: default nodes, Background grid, Controls, MiniMap.
 */

import { useCallback, useEffect, useMemo } from 'react';
import {
    ReactFlow,
    ReactFlowProvider,
    Background,
    Controls,
    MiniMap,
    BackgroundVariant,
    useReactFlow,
    type Node,
    type Edge,
    type OnNodesChange,
    type OnEdgesChange,
    type NodeTypes,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

export interface WorkflowCanvasProps {
    nodes: Node[];
    edges: Edge[];
    onNodesChange: OnNodesChange;
    onEdgesChange: OnEdgesChange;
    /** Optional custom node types (Phase 2). */
    nodeTypes?: NodeTypes;
    className?: string;
    /** When true, nodes/edges are not editable (future overview). */
    readOnly?: boolean;
}

function FitViewOnLoad({ nodeCount }: { nodeCount: number }) {
    const { fitView } = useReactFlow();

    useEffect(() => {
        if (nodeCount > 0) {
            // Small delay so layout has measured node sizes
            const id = requestAnimationFrame(() => {
                fitView({ padding: 0.2, duration: 200 });
            });
            return () => cancelAnimationFrame(id);
        }
    }, [nodeCount, fitView]);

    return null;
}

function CanvasInner({
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    nodeTypes,
    className,
    readOnly = false,
}: WorkflowCanvasProps) {
    const defaultEdgeOptions = useMemo(
        () => ({
            style: { stroke: 'var(--muted-foreground)', strokeWidth: 1.5 },
        }),
        [],
    );

    const onInit = useCallback(() => {
        // no-op; FitViewOnLoad handles fit
    }, []);

    return (
        <div
            className={className ?? 'h-full w-full'}
            data-testid="workflow-canvas"
            style={{
                // Theme-friendly canvas chrome
                ['--xy-background-color' as string]: 'var(--background)',
                ['--xy-minimap-background-color' as string]: 'var(--card, var(--background))',
                ['--xy-controls-button-background-color' as string]: 'var(--card, var(--background))',
                ['--xy-controls-button-color' as string]: 'var(--foreground)',
                ['--xy-controls-button-border-color' as string]: 'var(--border)',
                ['--xy-node-background-color' as string]: 'var(--card, var(--background))',
                ['--xy-node-color' as string]: 'var(--foreground)',
                ['--xy-node-border' as string]: '1px solid var(--border)',
            }}
        >
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={readOnly ? undefined : onNodesChange}
                onEdgesChange={readOnly ? undefined : onEdgesChange}
                nodeTypes={nodeTypes}
                defaultEdgeOptions={defaultEdgeOptions}
                fitView
                onInit={onInit}
                nodesDraggable={!readOnly}
                nodesConnectable={!readOnly}
                elementsSelectable={!readOnly}
                proOptions={{ hideAttribution: true }}
                minZoom={0.25}
                maxZoom={2}
            >
                <Background
                    variant={BackgroundVariant.Dots}
                    gap={16}
                    size={1}
                    color="var(--border)"
                />
                <Controls showInteractive={!readOnly} />
                <MiniMap
                    pannable
                    zoomable
                    maskColor="color-mix(in oklab, var(--foreground) 10%, transparent)"
                    nodeColor="var(--muted-foreground)"
                />
                <FitViewOnLoad nodeCount={nodes.length} />
            </ReactFlow>
        </div>
    );
}

/**
 * Public canvas: wraps inner flow with ReactFlowProvider.
 */
export function WorkflowCanvas(props: WorkflowCanvasProps) {
    return (
        <ReactFlowProvider>
            <CanvasInner {...props} />
        </ReactFlowProvider>
    );
}

export default WorkflowCanvas;
