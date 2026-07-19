/**
 * Full-page workflow visual editor (create + edit).
 * Phase 2: trigger node, custom cards, palette, properties, edge wiring.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import {
    useNodesState,
    useEdgesState,
    type Node,
    type Edge,
    type OnSelectionChangeParams,
} from '@xyflow/react';
import { ArrowLeft, Save } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';
import {
    workflowsService,
    type Workflow,
    type WorkflowStep,
    type WorkflowTriggerConfig,
} from '@/services/workflows.service';
import type { StepTypeValue } from '../workflowConstants';
import { WorkflowCanvas } from './WorkflowCanvas';
import {
    stepsToFlow,
    flowToPayload,
    createEmptyFlow,
    isStepNodeData,
    isTriggerNodeData,
} from './graphMapper';
import { validateStepNames, validateGraphEdges } from './graphValidation';
import {
    createDefaultStep,
    generateUniqueStepName,
    removeNodeAndEdges,
    renameNode,
} from './nodeDefaults';
import { NodePalette } from './palette/NodePalette';
import { PropertiesPanel } from './properties/PropertiesPanel';

interface EditorMeta {
    name: string;
    description: string;
    enabled: boolean;
}

const DEFAULT_META: EditorMeta = {
    name: '',
    description: '',
    enabled: true,
};

function workflowToMeta(wf: Workflow): EditorMeta {
    return {
        name: wf.name,
        description: wf.description ?? '',
        enabled: wf.enabled,
    };
}

export default function WorkflowEditorPage() {
    const { id } = useParams<{ id: string }>();
    const isEdit = Boolean(id);
    const navigate = useNavigate();
    const { toast } = useToast();

    const [meta, setMeta] = useState<EditorMeta>(DEFAULT_META);
    const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
    const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
    const [loading, setLoading] = useState(isEdit);
    const [saving, setSaving] = useState(false);
    const [loadError, setLoadError] = useState<string | null>(null);

    const nodesRef = useRef(nodes);
    const edgesRef = useRef(edges);
    nodesRef.current = nodes;
    edgesRef.current = edges;

    const setMetaField = useCallback(<K extends keyof EditorMeta>(key: K, value: EditorMeta[K]) => {
        setMeta((prev) => ({ ...prev, [key]: value }));
    }, []);

    // Load existing workflow or seed new graph
    useEffect(() => {
        if (!id) {
            setLoading(false);
            setLoadError(null);
            setMeta(DEFAULT_META);
            const empty = createEmptyFlow({ type: 'manual' });
            setNodes(empty.nodes);
            setEdges(empty.edges);
            setSelectedNodeId(null);
            return;
        }

        let cancelled = false;
        setLoading(true);
        setLoadError(null);

        (async () => {
            try {
                const wf = await workflowsService.get(id);
                if (cancelled) return;
                setMeta(workflowToMeta(wf));
                const graph = stepsToFlow(wf.steps, wf.trigger_config);
                setNodes(graph.nodes);
                setEdges(graph.edges);
                setSelectedNodeId(null);
            } catch {
                if (!cancelled) {
                    setLoadError('Workflow not found or failed to load.');
                }
            } finally {
                if (!cancelled) setLoading(false);
            }
        })();

        return () => {
            cancelled = true;
        };
    }, [id, setNodes, setEdges]);

    // Listen for delete from node card hover control
    useEffect(() => {
        const handler = (e: Event) => {
            const detail = (e as CustomEvent<{ nodeId: string }>).detail;
            if (!detail?.nodeId) return;
            const result = removeNodeAndEdges(nodesRef.current, edgesRef.current, detail.nodeId);
            setNodes(result.nodes);
            setEdges(result.edges);
            setSelectedNodeId((cur) => (cur === detail.nodeId ? null : cur));
        };
        window.addEventListener('workflow-node-delete', handler);
        return () => window.removeEventListener('workflow-node-delete', handler);
    }, [setNodes, setEdges]);

    const onSelectionChange = useCallback(({ nodes: selected }: OnSelectionChangeParams) => {
        setSelectedNodeId(selected[0]?.id ?? null);
    }, []);

    const addStepAt = useCallback(
        (stepType: StepTypeValue, position: { x: number; y: number }) => {
            setNodes((nds) => {
                const name = generateUniqueStepName(
                    stepType,
                    nds.map((n) => n.id),
                );
                const step = createDefaultStep(stepType, name);
                const node: Node = {
                    id: name,
                    type: stepType,
                    position,
                    selected: true,
                    data: {
                        kind: 'step',
                        label: name,
                        step,
                    },
                };
                // Deselect others
                const cleared = nds.map((n) => ({ ...n, selected: false }));
                setSelectedNodeId(name);
                return [...cleared, node];
            });
        },
        [setNodes],
    );

    const handleAddFromPalette = useCallback(
        (stepType: StepTypeValue) => {
            // Place near center-right of existing content
            const xs = nodes.map((n) => n.position.x);
            const ys = nodes.map((n) => n.position.y);
            const x = xs.length ? Math.max(...xs) + 220 : 320;
            const y = ys.length ? ys.reduce((a, b) => a + b, 0) / ys.length : 120;
            addStepAt(stepType, { x, y });
        },
        [nodes, addStepAt],
    );

    const handleDropStepType = useCallback(
        (stepType: StepTypeValue, position: { x: number; y: number }) => {
            addStepAt(stepType, position);
        },
        [addStepAt],
    );

    const handleConnectEdges = useCallback(
        (next: Edge[]) => {
            setEdges(next);
        },
        [setEdges],
    );

    const handleUpdateTrigger = useCallback(
        (trigger: WorkflowTriggerConfig) => {
            setNodes((nds) =>
                nds.map((n) => {
                    if (!isTriggerNodeData(n.data) && n.type !== 'trigger') return n;
                    return {
                        ...n,
                        data: {
                            kind: 'trigger' as const,
                            label: 'Trigger',
                            trigger,
                        },
                    };
                }),
            );
        },
        [setNodes],
    );

    const handleUpdateStep = useCallback(
        (nodeId: string, step: WorkflowStep) => {
            setNodes((nds) =>
                nds.map((n) => {
                    if (n.id !== nodeId) return n;
                    return {
                        ...n,
                        data: {
                            kind: 'step' as const,
                            label: step.name || n.id,
                            step: { ...step, name: step.name || n.id },
                        },
                    };
                }),
            );
        },
        [setNodes],
    );

    const handleRenameStep = useCallback(
        (nodeId: string, newName: string) => {
            const trimmed = newName.trim();
            if (!trimmed || trimmed === nodeId) {
                // Still sync label if only whitespace difference on empty attempt
                if (!trimmed) return;
            }
            setNodes((nds) => {
                const result = renameNode(
                    nds as { id: string; data?: Record<string, unknown>; [k: string]: unknown }[],
                    edges as { id: string; source: string; target: string; [k: string]: unknown }[],
                    nodeId,
                    trimmed,
                );
                setEdges(result.edges as Edge[]);
                if (trimmed !== nodeId) {
                    setSelectedNodeId(trimmed);
                }
                return result.nodes as Node[];
            });
        },
        [edges, setNodes, setEdges],
    );

    const handleDeleteNode = useCallback(
        (nodeId: string) => {
            const result = removeNodeAndEdges(nodes, edges, nodeId);
            setNodes(result.nodes);
            setEdges(result.edges);
            setSelectedNodeId((cur) => (cur === nodeId ? null : cur));
        },
        [nodes, edges, setNodes, setEdges],
    );

    const title = useMemo(() => {
        if (isEdit) return meta.name || 'Edit Workflow';
        return 'New Workflow';
    }, [isEdit, meta.name]);

    const handleSave = async () => {
        if (!meta.name.trim()) {
            toast({ title: 'Name is required', variant: 'destructive' });
            return;
        }

        const { trigger, steps } = flowToPayload(nodes, edges);
        const nameError = validateStepNames(steps);
        if (nameError) {
            toast({ title: nameError, variant: 'destructive' });
            return;
        }
        const edgeError = validateGraphEdges(edges);
        if (edgeError) {
            toast({ title: edgeError, variant: 'destructive' });
            return;
        }

        // Validate action configs are objects
        for (const s of steps) {
            if (s.type === 'action' && s.config != null && typeof s.config !== 'object') {
                toast({
                    title: `Action "${s.name}" has invalid config JSON`,
                    variant: 'destructive',
                });
                return;
            }
        }

        // Flag action nodes still holding invalid JSON in panel: config must be object
        for (const n of nodes) {
            if (!isStepNodeData(n.data) || n.data.step.type !== 'action') continue;
            const cfg = n.data.step.config;
            if (cfg !== undefined && cfg !== null && (typeof cfg !== 'object' || Array.isArray(cfg))) {
                toast({
                    title: `Action "${n.id}" has invalid config`,
                    variant: 'destructive',
                });
                return;
            }
        }

        setSaving(true);
        try {
            if (isEdit && id) {
                await workflowsService.update(id, {
                    name: meta.name.trim(),
                    description: meta.description.trim() || undefined,
                    trigger,
                    steps,
                    enabled: meta.enabled,
                });
                toast({ title: 'Workflow updated' });
            } else {
                const created = await workflowsService.create({
                    name: meta.name.trim(),
                    description: meta.description.trim() || undefined,
                    trigger,
                    steps,
                    enabled: meta.enabled,
                });
                toast({ title: 'Workflow created' });
                navigate(`/admin/workflows/${created.id}/edit`, { replace: true });
            }
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Failed to save workflow';
            toast({ title: 'Error', description: msg, variant: 'destructive' });
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return (
            <div className="flex flex-col h-full min-h-0 p-6 space-y-4" data-testid="workflow-editor-loading">
                <Skeleton className="h-10 w-64" />
                <Skeleton className="flex-1 w-full min-h-[400px]" />
            </div>
        );
    }

    if (loadError) {
        return (
            <div
                className="flex flex-col items-center justify-center h-full min-h-[320px] gap-4 p-8"
                data-testid="workflow-editor-error"
            >
                <p className="text-destructive font-medium">{loadError}</p>
                <Button asChild variant="outline">
                    <Link to="/admin/workflows">Back to Workflows</Link>
                </Button>
            </div>
        );
    }

    return (
        <div
            className="flex flex-col h-full min-h-0 bg-background"
            data-testid="workflow-editor-page"
        >
            <header className="flex flex-wrap items-center gap-3 border-b px-4 py-3 shrink-0 bg-background">
                <Button variant="ghost" size="sm" asChild>
                    <Link to="/admin/workflows" className="gap-1.5">
                        <ArrowLeft className="h-4 w-4" />
                        Workflows
                    </Link>
                </Button>

                <div className="h-6 w-px bg-border hidden sm:block" />

                <div className="flex flex-1 flex-wrap items-center gap-3 min-w-0">
                    <div className="flex flex-col gap-0.5 min-w-[160px] flex-1 max-w-sm">
                        <Label htmlFor="wf-name" className="sr-only">
                            Name
                        </Label>
                        <Input
                            id="wf-name"
                            value={meta.name}
                            onChange={(e) => setMetaField('name', e.target.value)}
                            placeholder="Workflow name"
                            className="h-9 font-medium"
                            data-testid="workflow-editor-name"
                        />
                    </div>

                    <div className="flex items-center gap-2">
                        <Switch
                            id="wf-enabled"
                            checked={meta.enabled}
                            onCheckedChange={(v) => setMetaField('enabled', v)}
                        />
                        <Label htmlFor="wf-enabled" className="text-sm text-muted-foreground">
                            Enabled
                        </Label>
                    </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                    <Button variant="outline" size="sm" asChild>
                        <Link to="/admin/workflows">Cancel</Link>
                    </Button>
                    <Button size="sm" onClick={handleSave} disabled={saving} data-testid="workflow-editor-save">
                        <Save className="h-4 w-4 mr-1.5" />
                        {saving ? 'Saving…' : 'Save'}
                    </Button>
                </div>
            </header>

            <div className="border-b px-4 py-2 shrink-0">
                <Input
                    value={meta.description}
                    onChange={(e) => setMetaField('description', e.target.value)}
                    placeholder="Description (optional)"
                    className="h-8 text-sm border-0 shadow-none px-0 focus-visible:ring-0"
                    data-testid="workflow-editor-description"
                />
                <p className="text-xs text-muted-foreground mt-0.5 truncate" title={title}>
                    {isEdit
                        ? `Editing · ${id}`
                        : 'Drag steps from the palette · connect handles to set flow'}
                </p>
            </div>

            <div className="flex flex-1 min-h-0">
                <div className="w-[220px] shrink-0 border-r bg-muted/20">
                    <NodePalette onAddStep={handleAddFromPalette} />
                </div>

                <main className="flex-1 min-w-0 min-h-0 relative">
                    <WorkflowCanvas
                        nodes={nodes}
                        edges={edges}
                        onNodesChange={onNodesChange}
                        onEdgesChange={onEdgesChange}
                        onConnectEdges={handleConnectEdges}
                        onSelectionChange={onSelectionChange}
                        onDropStepType={handleDropStepType}
                        className="absolute inset-0"
                    />
                </main>

                <div className="w-[300px] shrink-0 border-l bg-muted/20">
                    <PropertiesPanel
                        nodes={nodes}
                        edges={edges}
                        selectedNodeId={selectedNodeId}
                        meta={meta}
                        onMetaChange={setMetaField}
                        onUpdateTrigger={handleUpdateTrigger}
                        onUpdateStep={handleUpdateStep}
                        onRenameStep={handleRenameStep}
                        onDeleteNode={handleDeleteNode}
                    />
                </div>
            </div>
        </div>
    );
}
