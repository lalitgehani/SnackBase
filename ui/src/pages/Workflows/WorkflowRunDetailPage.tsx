/**
 * Run detail: read-only graph with step-log status overlay.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router';
import {
    type Node,
    type Edge,
    type OnSelectionChangeParams,
} from '@xyflow/react';
import { ArrowLeft, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';
import {
    workflowsService,
    type Workflow,
    type WorkflowInstanceDetail,
} from '@/services/workflows.service';
import { WorkflowCanvas } from './editor/WorkflowCanvas';
import { buildReadonlyGraph } from './editor/buildReadonlyGraph';
import {
    applyRunStatusToNodes,
    getLogForNode,
    mapStepLogsToNodeStatus,
    type NodeRunStatus,
} from './editor/runStatusMapper';
import { isStepNodeData, isTriggerNodeData } from './editor/graphMapper';
import { StepLogPanel } from './run/StepLogPanel';
import {
    formatWorkflowDate,
    InstanceStatusBadge,
} from './InstanceStatusBadge';

export default function WorkflowRunDetailPage() {
    const { id, instanceId } = useParams<{ id: string; instanceId: string }>();
    const { toast } = useToast();

    const [workflow, setWorkflow] = useState<Workflow | null>(null);
    const [instance, setInstance] = useState<WorkflowInstanceDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
    const [cancelling, setCancelling] = useState(false);
    const [resuming, setResuming] = useState(false);
    const [fitViewToken, setFitViewToken] = useState(0);

    const load = useCallback(async () => {
        if (!id || !instanceId) return;
        setLoading(true);
        setError(null);
        try {
            const [wf, inst] = await Promise.all([
                workflowsService.get(id),
                workflowsService.getInstance(instanceId),
            ]);
            if (inst.workflow_id !== wf.id) {
                setError('This run does not belong to the requested workflow.');
                setWorkflow(null);
                setInstance(null);
                return;
            }
            setWorkflow(wf);
            setInstance(inst);
            setFitViewToken((t) => t + 1);
        } catch {
            setError('Failed to load run detail.');
            setWorkflow(null);
            setInstance(null);
        } finally {
            setLoading(false);
        }
    }, [id, instanceId]);

    useEffect(() => {
        load();
    }, [load]);

    const { nodes, edges } = useMemo(() => {
        if (!workflow || !instance) {
            return { nodes: [] as Node[], edges: [] as Edge[] };
        }
        const graph = buildReadonlyGraph(workflow);
        const statusMap = mapStepLogsToNodeStatus(instance.step_logs, instance);
        return {
            nodes: applyRunStatusToNodes(graph.nodes, statusMap),
            edges: graph.edges,
        };
    }, [workflow, instance]);

    const selectedNode = useMemo(
        () => (selectedNodeId ? nodes.find((n) => n.id === selectedNodeId) ?? null : null),
        [nodes, selectedNodeId],
    );

    const selectedLog = useMemo(() => {
        if (!instance || !selectedNodeId) return null;
        return getLogForNode(instance.step_logs, selectedNodeId);
    }, [instance, selectedNodeId]);

    const selectedRunStatus: NodeRunStatus | null = useMemo(() => {
        if (!selectedNode) return null;
        if (isStepNodeData(selectedNode.data) || isTriggerNodeData(selectedNode.data)) {
            return selectedNode.data.runStatus ?? null;
        }
        return null;
    }, [selectedNode]);

    const onSelectionChange = useCallback((params: OnSelectionChangeParams) => {
        const n = params.nodes[0];
        setSelectedNodeId(n?.id ?? null);
    }, []);

    const handleCancel = async () => {
        if (!instance) return;
        setCancelling(true);
        try {
            await workflowsService.cancelInstance(instance.id);
            toast({ title: 'Instance cancelled' });
            await load();
        } catch {
            toast({
                title: 'Error',
                description: 'Failed to cancel instance',
                variant: 'destructive',
            });
        } finally {
            setCancelling(false);
        }
    };

    const handleResume = async () => {
        if (!instance) return;
        setResuming(true);
        try {
            await workflowsService.resumeInstance(instance.id);
            toast({ title: 'Resume started' });
            setTimeout(() => load(), 800);
        } catch {
            toast({
                title: 'Error',
                description: 'Failed to resume instance',
                variant: 'destructive',
            });
        } finally {
            setResuming(false);
        }
    };

    if (loading) {
        return (
            <div className="flex flex-col h-full p-6 gap-4" data-testid="run-detail-loading">
                <Skeleton className="h-8 w-64" />
                <Skeleton className="h-full w-full min-h-[320px]" />
            </div>
        );
    }

    if (error || !workflow || !instance) {
        return (
            <div
                className="flex flex-col items-center justify-center h-full gap-4 p-6"
                data-testid="run-detail-error"
            >
                <p className="text-sm text-destructive">{error ?? 'Run not found.'}</p>
                <Button variant="outline" asChild>
                    <Link to={id ? `/admin/workflows/${id}` : '/admin/workflows'}>
                        Back to overview
                    </Link>
                </Button>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full min-h-0" data-testid="workflow-run-detail-page">
            <div className="shrink-0 border-b bg-background px-4 py-3 flex flex-wrap items-center gap-3">
                <Button variant="ghost" size="sm" asChild className="h-8 px-2">
                    <Link
                        to={`/admin/workflows/${workflow.id}`}
                        data-testid="run-detail-back"
                    >
                        <ArrowLeft className="h-4 w-4 mr-1" />
                        {workflow.name}
                    </Link>
                </Button>
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                        <h1 className="text-lg font-semibold">Run detail</h1>
                        <InstanceStatusBadge status={instance.status} />
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5 truncate">
                        <span className="font-mono">{instance.id}</span>
                        {' · '}
                        Started {formatWorkflowDate(instance.started_at)}
                        {instance.completed_at
                            ? ` · Completed ${formatWorkflowDate(instance.completed_at)}`
                            : ''}
                    </p>
                </div>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={() => load()}
                    data-testid="run-detail-refresh"
                >
                    <RefreshCw className="h-4 w-4 mr-1" />
                    Refresh
                </Button>
            </div>

            <div className="flex flex-1 min-h-0 min-w-0">
                <div className="flex-1 min-w-0 min-h-[320px] relative">
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
                <StepLogPanel
                    instance={instance}
                    selectedNode={selectedNode}
                    stepLog={selectedLog}
                    runStatus={selectedRunStatus}
                    onCancel={handleCancel}
                    onResume={handleResume}
                    cancelling={cancelling}
                    resuming={resuming}
                />
            </div>
        </div>
    );
}
