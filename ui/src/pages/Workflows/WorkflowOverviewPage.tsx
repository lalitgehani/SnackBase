/**
 * Workflow overview: metadata, read-only graph, recent instances.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import {
    type Node,
    type Edge,
    type OnSelectionChangeParams,
} from '@xyflow/react';
import {
    ArrowLeft,
    Pencil,
    Play,
    Trash2,
    RefreshCw,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { useToast } from '@/hooks/use-toast';
import {
    workflowsService,
    type Workflow,
    type WorkflowInstance,
} from '@/services/workflows.service';
import { WorkflowCanvas } from './editor/WorkflowCanvas';
import { buildReadonlyGraph } from './editor/buildReadonlyGraph';
import { triggerSummary } from './editor/graphMapper';
import { ReadonlyConfigPanel } from './overview/ReadonlyConfigPanel';
import {
    formatWorkflowDate,
    InstanceStatusBadge,
} from './InstanceStatusBadge';
import { DeleteWorkflowDialog } from './DeleteWorkflowDialog';

const INSTANCES_LIMIT = 20;

export default function WorkflowOverviewPage() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const { toast } = useToast();

    const [workflow, setWorkflow] = useState<Workflow | null>(null);
    const [instances, setInstances] = useState<WorkflowInstance[]>([]);
    const [instancesTotal, setInstancesTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [instancesLoading, setInstancesLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [triggering, setTriggering] = useState(false);
    const [deleteOpen, setDeleteOpen] = useState(false);
    const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
    const [fitViewToken, setFitViewToken] = useState(0);

    const load = useCallback(async () => {
        if (!id) return;
        setLoading(true);
        setError(null);
        try {
            const wf = await workflowsService.get(id);
            setWorkflow(wf);
            setFitViewToken((t) => t + 1);
        } catch {
            setError('Failed to load workflow.');
            setWorkflow(null);
        } finally {
            setLoading(false);
        }
    }, [id]);

    const loadInstances = useCallback(async () => {
        if (!id) return;
        setInstancesLoading(true);
        try {
            const res = await workflowsService.listInstances(id, {
                limit: INSTANCES_LIMIT,
                offset: 0,
            });
            setInstances(res.items);
            setInstancesTotal(res.total);
        } catch {
            setInstances([]);
            setInstancesTotal(0);
        } finally {
            setInstancesLoading(false);
        }
    }, [id]);

    useEffect(() => {
        load();
        loadInstances();
    }, [load, loadInstances]);

    const { nodes, edges } = useMemo(() => {
        if (!workflow) return { nodes: [] as Node[], edges: [] as Edge[] };
        return buildReadonlyGraph(workflow);
    }, [workflow]);

    useEffect(() => {
        setSelectedNodeId(null);
    }, [workflow?.id]);

    const selectedNode = useMemo(
        () => (selectedNodeId ? nodes.find((n) => n.id === selectedNodeId) ?? null : null),
        [nodes, selectedNodeId],
    );

    const onSelectionChange = useCallback((params: OnSelectionChangeParams) => {
        const n = params.nodes[0];
        setSelectedNodeId(n?.id ?? null);
    }, []);

    const handleTrigger = async () => {
        if (!workflow) return;
        setTriggering(true);
        try {
            const result = await workflowsService.trigger(workflow.id);
            toast({
                title: 'Workflow triggered',
                description: `Instance ${result.instance_id.slice(0, 8)}… started`,
            });
            await loadInstances();
            navigate(`/admin/workflows/${workflow.id}/runs/${result.instance_id}`);
        } catch {
            toast({
                title: 'Error',
                description: 'Failed to trigger workflow',
                variant: 'destructive',
            });
        } finally {
            setTriggering(false);
        }
    };

    if (loading) {
        return (
            <div className="flex flex-col h-full p-6 gap-4" data-testid="workflow-overview-loading">
                <Skeleton className="h-8 w-64" />
                <Skeleton className="h-full w-full min-h-[320px]" />
            </div>
        );
    }

    if (error || !workflow) {
        return (
            <div className="flex flex-col items-center justify-center h-full gap-4 p-6" data-testid="workflow-overview-error">
                <p className="text-sm text-destructive">{error ?? 'Workflow not found.'}</p>
                <Button variant="outline" asChild>
                    <Link to="/admin/workflows">Back to Workflows</Link>
                </Button>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full min-h-0" data-testid="workflow-overview-page">
            {/* Header */}
            <div className="shrink-0 border-b bg-background px-4 py-3 flex flex-wrap items-center gap-3">
                <Button variant="ghost" size="sm" asChild className="h-8 px-2">
                    <Link to="/admin/workflows" data-testid="overview-back">
                        <ArrowLeft className="h-4 w-4 mr-1" />
                        Workflows
                    </Link>
                </Button>
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                        <h1 className="text-lg font-semibold truncate" data-testid="overview-name">
                            {workflow.name}
                        </h1>
                        <Badge variant={workflow.enabled ? 'default' : 'secondary'}>
                            {workflow.enabled ? 'Enabled' : 'Disabled'}
                        </Badge>
                        <Badge variant="outline" className="capitalize text-xs">
                            {workflow.trigger_type}
                        </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5 truncate">
                        {triggerSummary(workflow.trigger_config)}
                        {workflow.description ? ` · ${workflow.description}` : ''}
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={handleTrigger}
                        disabled={triggering}
                        data-testid="overview-run"
                    >
                        <Play className="h-4 w-4 mr-1" />
                        {triggering ? 'Running…' : 'Run'}
                    </Button>
                    <Button variant="default" size="sm" asChild data-testid="overview-edit">
                        <Link to={`/admin/workflows/${workflow.id}/edit`}>
                            <Pencil className="h-4 w-4 mr-1" />
                            Edit
                        </Link>
                    </Button>
                    <Button
                        variant="outline"
                        size="sm"
                        className="text-destructive hover:text-destructive"
                        onClick={() => setDeleteOpen(true)}
                        data-testid="overview-delete"
                    >
                        <Trash2 className="h-4 w-4" />
                    </Button>
                </div>
            </div>

            {/* Graph + panel */}
            <div className="flex flex-1 min-h-0 min-w-0">
                <div className="flex-1 min-w-0 min-h-[280px] relative">
                    <WorkflowCanvas
                        nodes={nodes}
                        edges={edges}
                        onNodesChange={() => {}}
                        onEdgesChange={() => {}}
                        onSelectionChange={onSelectionChange}
                        readOnly
                        showToolbar={false}
                        fitViewToken={fitViewToken}
                        className="h-full w-full"
                    />
                </div>
                <ReadonlyConfigPanel workflow={workflow} selectedNode={selectedNode} />
            </div>

            {/* Recent instances */}
            <div className="shrink-0 border-t bg-background max-h-[240px] overflow-y-auto">
                <div className="px-4 py-2 flex items-center justify-between sticky top-0 bg-background border-b z-10">
                    <h2 className="text-sm font-medium">
                        Recent runs
                        {instancesTotal > 0 && (
                            <span className="text-muted-foreground font-normal ml-1">
                                ({instancesTotal})
                            </span>
                        )}
                    </h2>
                    <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 text-xs"
                        onClick={() => loadInstances()}
                        data-testid="overview-refresh-instances"
                    >
                        <RefreshCw className="h-3.5 w-3.5 mr-1" />
                        Refresh
                    </Button>
                </div>

                {instancesLoading ? (
                    <div className="p-4 space-y-2">
                        {[1, 2, 3].map((i) => (
                            <Skeleton key={i} className="h-8 w-full" />
                        ))}
                    </div>
                ) : instances.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-8 px-4">
                        No instances yet. Run the workflow to start one.
                    </p>
                ) : (
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead className="text-xs">Status</TableHead>
                                <TableHead className="text-xs">Current step</TableHead>
                                <TableHead className="text-xs">Started</TableHead>
                                <TableHead className="text-xs">Completed</TableHead>
                                <TableHead className="text-xs w-24" />
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {instances.map((inst) => (
                                <TableRow
                                    key={inst.id}
                                    className="cursor-pointer hover:bg-muted/40"
                                    onClick={() =>
                                        navigate(
                                            `/admin/workflows/${workflow.id}/runs/${inst.id}`,
                                        )
                                    }
                                    data-testid={`instance-row-${inst.id}`}
                                >
                                    <TableCell>
                                        <InstanceStatusBadge status={inst.status} />
                                    </TableCell>
                                    <TableCell className="text-xs font-mono text-muted-foreground">
                                        {inst.current_step ?? '—'}
                                    </TableCell>
                                    <TableCell className="text-xs text-muted-foreground">
                                        {formatWorkflowDate(inst.started_at)}
                                    </TableCell>
                                    <TableCell className="text-xs text-muted-foreground">
                                        {formatWorkflowDate(inst.completed_at)}
                                    </TableCell>
                                    <TableCell>
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            className="h-7 text-xs"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                navigate(
                                                    `/admin/workflows/${workflow.id}/runs/${inst.id}`,
                                                );
                                            }}
                                        >
                                            Open
                                        </Button>
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                )}
            </div>

            <DeleteWorkflowDialog
                workflow={workflow}
                open={deleteOpen}
                onOpenChange={setDeleteOpen}
                onDeleted={() => {
                    setDeleteOpen(false);
                    navigate('/admin/workflows');
                }}
            />
        </div>
    );
}
