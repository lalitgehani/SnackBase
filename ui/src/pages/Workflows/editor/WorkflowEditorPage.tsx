/**
 * Full-page workflow visual editor (create + edit).
 * Phase 1: shell, canvas, header metadata, save/load via graphMapper.
 * Trigger is workflow-level (not a canvas node until Phase 2.1).
 * Step palette/properties panels are placeholders until Phase 2.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import {
    useNodesState,
    useEdgesState,
    type Node,
    type Edge,
} from '@xyflow/react';
import { ArrowLeft, Save } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Skeleton } from '@/components/ui/skeleton';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';
import {
    workflowsService,
    type Workflow,
    type WorkflowTriggerConfig,
} from '@/services/workflows.service';
import { WORKFLOW_EVENTS } from '../WorkflowFormFields';
import { WorkflowCanvas } from './WorkflowCanvas';
import { stepsToFlow, flowToSteps } from './graphMapper';
import { validateStepNames, validateGraphEdges } from './graphValidation';

type TriggerType = 'event' | 'schedule' | 'manual' | 'webhook';

interface EditorMeta {
    name: string;
    description: string;
    enabled: boolean;
    triggerType: TriggerType;
    triggerEvent: string;
    triggerCollection: string;
    triggerCondition: string;
    triggerCron: string;
}

const DEFAULT_META: EditorMeta = {
    name: '',
    description: '',
    enabled: true,
    triggerType: 'manual',
    triggerEvent: 'records.create',
    triggerCollection: '',
    triggerCondition: '',
    triggerCron: '0 9 * * *',
};

function metaToTrigger(meta: EditorMeta): WorkflowTriggerConfig {
    switch (meta.triggerType) {
        case 'event':
            return {
                type: 'event',
                event: meta.triggerEvent,
                ...(meta.triggerCollection ? { collection: meta.triggerCollection } : {}),
                ...(meta.triggerCondition ? { condition: meta.triggerCondition } : {}),
            };
        case 'schedule':
            return { type: 'schedule', cron: meta.triggerCron };
        case 'webhook':
            return { type: 'webhook' };
        default:
            return { type: 'manual' };
    }
}

function workflowToMeta(wf: Workflow): EditorMeta {
    const tc = wf.trigger_config;
    return {
        name: wf.name,
        description: wf.description ?? '',
        enabled: wf.enabled,
        triggerType: (wf.trigger_type as TriggerType) || 'manual',
        triggerEvent: tc.type === 'event' ? tc.event : 'records.create',
        triggerCollection: tc.type === 'event' ? (tc.collection ?? '') : '',
        triggerCondition: tc.type === 'event' ? (tc.condition ?? '') : '',
        triggerCron: tc.type === 'schedule' ? tc.cron : '0 9 * * *',
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
    const [loading, setLoading] = useState(isEdit);
    const [saving, setSaving] = useState(false);
    const [loadError, setLoadError] = useState<string | null>(null);

    const setMetaField = useCallback(<K extends keyof EditorMeta>(key: K, value: EditorMeta[K]) => {
        setMeta((prev) => ({ ...prev, [key]: value }));
    }, []);

    // Load existing workflow in edit mode
    useEffect(() => {
        if (!id) {
            setLoading(false);
            setLoadError(null);
            setMeta(DEFAULT_META);
            setNodes([]);
            setEdges([]);
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

    const title = useMemo(() => {
        if (isEdit) return meta.name || 'Edit Workflow';
        return 'New Workflow';
    }, [isEdit, meta.name]);

    const handleSave = async () => {
        if (!meta.name.trim()) {
            toast({ title: 'Name is required', variant: 'destructive' });
            return;
        }

        const steps = flowToSteps(nodes, edges);
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

        setSaving(true);
        try {
            const trigger = metaToTrigger(meta);
            if (isEdit && id) {
                await workflowsService.update(id, {
                    name: meta.name.trim(),
                    description: meta.description.trim() || undefined,
                    trigger,
                    steps,
                    enabled: meta.enabled,
                });
                toast({ title: 'Workflow updated' });
                // Re-hydrate from local state is fine; optionally re-fetch
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
            {/* Editor chrome */}
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

                    <div className="flex items-center gap-2">
                        <Label className="text-xs text-muted-foreground shrink-0">Trigger</Label>
                        <Select
                            value={meta.triggerType}
                            onValueChange={(v) => setMetaField('triggerType', v as TriggerType)}
                        >
                            <SelectTrigger className="w-32 h-9" data-testid="workflow-editor-trigger-type">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="manual">Manual</SelectItem>
                                <SelectItem value="event">Event</SelectItem>
                                <SelectItem value="schedule">Schedule</SelectItem>
                                <SelectItem value="webhook">Webhook</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    {meta.triggerType === 'event' && (
                        <Select
                            value={meta.triggerEvent}
                            onValueChange={(v) => setMetaField('triggerEvent', v)}
                        >
                            <SelectTrigger className="w-48 h-9">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {WORKFLOW_EVENTS.map((ev) => (
                                    <SelectItem key={ev.value} value={ev.value}>
                                        {ev.label}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    )}

                    {meta.triggerType === 'event' && (
                        <Input
                            className="h-9 w-36"
                            placeholder="Collection"
                            value={meta.triggerCollection}
                            onChange={(e) => setMetaField('triggerCollection', e.target.value)}
                        />
                    )}

                    {meta.triggerType === 'schedule' && (
                        <Input
                            className="h-9 w-36 font-mono text-xs"
                            placeholder="Cron"
                            value={meta.triggerCron}
                            onChange={(e) => setMetaField('triggerCron', e.target.value)}
                        />
                    )}
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

            {/* Optional description row */}
            <div className="border-b px-4 py-2 shrink-0">
                <Input
                    value={meta.description}
                    onChange={(e) => setMetaField('description', e.target.value)}
                    placeholder="Description (optional)"
                    className="h-8 text-sm border-0 shadow-none px-0 focus-visible:ring-0"
                    data-testid="workflow-editor-description"
                />
                <p className="text-xs text-muted-foreground mt-0.5 truncate" title={title}>
                    {isEdit ? `Editing · ${id}` : 'Create a new workflow · drag nodes once steps are loaded'}
                </p>
            </div>

            {/* Three-pane body */}
            <div className="flex flex-1 min-h-0">
                {/* Left palette placeholder */}
                <aside
                    className="w-[220px] shrink-0 border-r bg-muted/20 p-4 flex flex-col gap-2"
                    data-testid="workflow-editor-palette"
                >
                    <p className="text-sm font-medium">Palette</p>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                        Step types will appear here in a later release. For now, open an existing
                        workflow to reposition steps, or create an empty workflow and add steps via
                        the API / legacy tools.
                    </p>
                </aside>

                {/* Center canvas */}
                <main className="flex-1 min-w-0 min-h-0 relative">
                    <WorkflowCanvas
                        nodes={nodes}
                        edges={edges}
                        onNodesChange={onNodesChange}
                        onEdgesChange={onEdgesChange}
                        className="absolute inset-0"
                    />
                </main>

                {/* Right properties placeholder */}
                <aside
                    className="w-[280px] shrink-0 border-l bg-muted/20 p-4 flex flex-col gap-2"
                    data-testid="workflow-editor-properties"
                >
                    <p className="text-sm font-medium">Properties</p>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                        Select a node to edit its configuration here (coming soon). Workflow name,
                        enabled state, and trigger are edited in the header.
                    </p>
                    {nodes.length > 0 && (
                        <div className="mt-4 space-y-1">
                            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                                Steps ({nodes.length})
                            </p>
                            <ul className="text-xs space-y-1 max-h-48 overflow-y-auto">
                                {nodes.map((n) => (
                                    <li key={n.id} className="font-mono truncate">
                                        {n.id}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </aside>
            </div>
        </div>
    );
}
