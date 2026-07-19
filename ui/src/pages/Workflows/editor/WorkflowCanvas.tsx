/**
 * React Flow host for the workflow visual editor.
 * Phase 2–3: custom nodes, connections, palette drop, toolbar.
 */

import { useCallback, useEffect, useMemo, useRef } from 'react';
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
    type OnConnect,
    type OnSelectionChangeFunc,
    type NodeTypes,
    type Connection,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { workflowNodeTypes } from './nodes';
import { applyConnection, validateConnection } from './connectionRules';
import { PALETTE_DND_TYPE, type StepTypeValue } from '../workflowConstants';
import { CanvasToolbar } from './CanvasToolbar';

export interface WorkflowCanvasProps {
    nodes: Node[];
    edges: Edge[];
    onNodesChange: OnNodesChange;
    onEdgesChange: OnEdgesChange;
    onConnectEdges?: (edges: Edge[]) => void;
    onSelectionChange?: OnSelectionChangeFunc;
    onDropStepType?: (stepType: StepTypeValue, position: { x: number; y: number }) => void;
    onAutoLayout?: () => void;
    onDeleteSelected?: () => void;
    canDelete?: boolean;
    /** Bump to re-run fitView (e.g. after template load or auto-layout). */
    fitViewToken?: number;
    nodeTypes?: NodeTypes;
    className?: string;
    readOnly?: boolean;
    showToolbar?: boolean;
}

function FitViewOnLoad({
    nodeCount,
    fitViewToken,
}: {
    nodeCount: number;
    fitViewToken?: number;
}) {
    const { fitView } = useReactFlow();
    const fittedFor = useRef<number | null>(null);
    const lastToken = useRef<number | undefined>(undefined);

    useEffect(() => {
        // Fit only when graph first gains nodes or count changes from empty
        if (nodeCount > 0 && fittedFor.current !== nodeCount && fittedFor.current === null) {
            const id = requestAnimationFrame(() => {
                fitView({ padding: 0.2, duration: 200 });
                fittedFor.current = nodeCount;
            });
            return () => cancelAnimationFrame(id);
        }
        if (nodeCount === 0) {
            fittedFor.current = null;
        }
    }, [nodeCount, fitView]);

    useEffect(() => {
        if (fitViewToken === undefined) return;
        if (lastToken.current === fitViewToken) return;
        lastToken.current = fitViewToken;
        const id = requestAnimationFrame(() => {
            fitView({ padding: 0.2, duration: 200 });
        });
        return () => cancelAnimationFrame(id);
    }, [fitViewToken, fitView]);

    return null;
}

function CanvasDropTarget({
    onDropStepType,
    readOnly,
}: {
    onDropStepType?: (stepType: StepTypeValue, position: { x: number; y: number }) => void;
    readOnly: boolean;
}) {
    const { screenToFlowPosition } = useReactFlow();
    const wrapperRef = useRef<HTMLDivElement | null>(null);

    useEffect(() => {
        const el = wrapperRef.current?.parentElement;
        if (!el || readOnly || !onDropStepType) return;

        const onDragOver = (e: DragEvent) => {
            e.preventDefault();
            if (e.dataTransfer) e.dataTransfer.dropEffect = 'move';
        };

        const onDrop = (e: DragEvent) => {
            e.preventDefault();
            const stepType = e.dataTransfer?.getData(PALETTE_DND_TYPE) as StepTypeValue | undefined;
            if (!stepType) return;
            const position = screenToFlowPosition({ x: e.clientX, y: e.clientY });
            onDropStepType(stepType, position);
        };

        el.addEventListener('dragover', onDragOver);
        el.addEventListener('drop', onDrop);
        return () => {
            el.removeEventListener('dragover', onDragOver);
            el.removeEventListener('drop', onDrop);
        };
    }, [onDropStepType, readOnly, screenToFlowPosition]);

    return <div ref={wrapperRef} className="hidden" aria-hidden />;
}

function CanvasInner({
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onConnectEdges,
    onSelectionChange,
    onDropStepType,
    onAutoLayout,
    onDeleteSelected,
    canDelete = false,
    fitViewToken,
    nodeTypes,
    className,
    readOnly = false,
    showToolbar = true,
}: WorkflowCanvasProps) {
    const types = nodeTypes ?? workflowNodeTypes;

    const defaultEdgeOptions = useMemo(
        () => ({
            type: 'smoothstep' as const,
            style: { stroke: 'var(--muted-foreground)', strokeWidth: 1.5 },
        }),
        [],
    );

    const isValidConnection = useCallback(
        (connection: Connection | Edge) => {
            return validateConnection(connection, nodes, edges).ok;
        },
        [nodes, edges],
    );

    const onConnect: OnConnect = useCallback(
        (connection) => {
            if (readOnly || !onConnectEdges) return;
            const next = applyConnection(connection, nodes, edges);
            if (next) onConnectEdges(next);
        },
        [readOnly, onConnectEdges, nodes, edges],
    );

    return (
        <div
            className={className ?? 'h-full w-full'}
            data-testid="workflow-canvas"
            style={{
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
            {showToolbar && onAutoLayout && onDeleteSelected && (
                <CanvasToolbar
                    onAutoLayout={onAutoLayout}
                    onDeleteSelected={onDeleteSelected}
                    canDelete={canDelete}
                    readOnly={readOnly}
                />
            )}
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={readOnly ? undefined : onNodesChange}
                onEdgesChange={readOnly ? undefined : onEdgesChange}
                onConnect={readOnly ? undefined : onConnect}
                isValidConnection={isValidConnection}
                onSelectionChange={onSelectionChange}
                nodeTypes={types}
                defaultEdgeOptions={defaultEdgeOptions}
                fitView
                nodesDraggable={!readOnly}
                nodesConnectable={!readOnly}
                elementsSelectable
                // Editor owns Delete/Backspace with focus guards (Phase 3)
                deleteKeyCode={null}
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
                <FitViewOnLoad nodeCount={nodes.length} fitViewToken={fitViewToken} />
                <CanvasDropTarget onDropStepType={onDropStepType} readOnly={readOnly} />
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
