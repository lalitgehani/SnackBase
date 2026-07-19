/**
 * Hook overview: read-only config, action cards, expandable executions.
 */

import { Fragment, useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import {
  ArrowLeft,
  ChevronDown,
  ChevronRight,
  Pencil,
  Play,
  RefreshCw,
  Trash2,
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
  hooksService,
  type Hook,
  type HookExecution,
} from '@/services/hooks.service';
import {
  TriggerBadge,
  triggerSummary,
  formatHookDate,
  formatDurationMs,
  ExecutionStatusBadge,
  actionSummary,
  actionAccentClass,
} from './HookStatusBadge';
import { DeleteHookDialog } from './DeleteHookDialog';
import { cn } from '@/lib/utils';

export default function HookOverviewPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();

  const [hook, setHook] = useState<Hook | null>(null);
  const [executions, setExecutions] = useState<HookExecution[]>([]);
  const [loading, setLoading] = useState(true);
  const [executionsLoading, setExecutionsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [triggering, setTriggering] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const h = await hooksService.get(id);
      setHook(h);
    } catch {
      setError('Failed to load hook.');
      setHook(null);
    } finally {
      setLoading(false);
    }
  }, [id]);

  const loadExecutions = useCallback(async () => {
    if (!id) return;
    setExecutionsLoading(true);
    try {
      const res = await hooksService.listExecutions(id);
      setExecutions(res.items);
    } catch {
      setExecutions([]);
    } finally {
      setExecutionsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
    loadExecutions();
  }, [load, loadExecutions]);

  const handleTrigger = async () => {
    if (!hook) return;
    setTriggering(true);
    try {
      const result = await hooksService.trigger(hook.id);
      toast({
        title: result.status === 'success' ? 'Hook executed' : 'Hook triggered',
        description:
          result.error ?? result.message ?? `${result.actions_executed} action(s) executed`,
      });
      await Promise.all([loadExecutions(), load()]);
    } catch {
      toast({
        title: 'Error',
        description: 'Failed to trigger hook',
        variant: 'destructive',
      });
    } finally {
      setTriggering(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col h-full p-6 gap-4" data-testid="hook-overview-loading">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-full w-full min-h-[240px]" />
      </div>
    );
  }

  if (error || !hook) {
    return (
      <div
        className="flex flex-col items-center justify-center h-full gap-4 p-6"
        data-testid="hook-overview-error"
      >
        <p className="text-sm text-destructive">{error ?? 'Hook not found.'}</p>
        <Button variant="outline" asChild>
          <Link to="/admin/hooks">Back to Hooks</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full min-h-0" data-testid="hook-overview-page">
      {/* Header */}
      <div className="shrink-0 border-b bg-background px-4 py-3 flex flex-wrap items-center gap-3">
        <Button variant="ghost" size="sm" asChild className="h-8 px-2">
          <Link to="/admin/hooks" data-testid="overview-back">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Hooks
          </Link>
        </Button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-lg font-semibold truncate" data-testid="overview-name">
              {hook.name}
            </h1>
            <Badge variant={hook.enabled ? 'default' : 'secondary'}>
              {hook.enabled ? 'Enabled' : 'Disabled'}
            </Badge>
            <TriggerBadge triggerType={hook.trigger.type} />
          </div>
          <p className="text-xs text-muted-foreground mt-0.5 truncate">
            {triggerSummary(hook)}
            {hook.description ? ` · ${hook.description}` : ''}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => void handleTrigger()}
            disabled={triggering}
            data-testid="overview-run"
          >
            <Play className="h-4 w-4 mr-1" />
            {triggering ? 'Running…' : 'Run'}
          </Button>
          <Button variant="outline" size="sm" asChild data-testid="overview-edit">
            <Link to={`/admin/hooks/${hook.id}/edit`}>
              <Pencil className="h-4 w-4 mr-1" />
              Edit
            </Link>
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setDeleteOpen(true)}
            data-testid="overview-delete"
          >
            <Trash2 className="h-4 w-4 mr-1" />
            Delete
          </Button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 min-h-0 overflow-y-auto p-6 space-y-6">
        <div className="grid gap-4 lg:grid-cols-2">
          {/* Left: config summary */}
          <div className="rounded-lg border p-4 space-y-3" data-testid="overview-config">
            <p className="text-sm font-medium">Configuration</p>
            <dl className="text-sm space-y-2">
              <div className="flex justify-between gap-2">
                <dt className="text-muted-foreground">Trigger</dt>
                <dd className="text-right">{triggerSummary(hook)}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-muted-foreground">Condition</dt>
                <dd className="font-mono text-xs text-right max-w-[70%] truncate">
                  {hook.condition || '—'}
                </dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-muted-foreground">Created</dt>
                <dd>{formatHookDate(hook.created_at)}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-muted-foreground">Updated</dt>
                <dd>{formatHookDate(hook.updated_at)}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-muted-foreground">Last run</dt>
                <dd data-testid="overview-last-run">{formatHookDate(hook.last_run_at)}</dd>
              </div>
            </dl>
          </div>

          {/* Right: action cards */}
          <div className="rounded-lg border p-4 space-y-3" data-testid="overview-actions">
            <p className="text-sm font-medium">
              Actions ({hook.actions.length})
            </p>
            {hook.actions.length === 0 ? (
              <p className="text-sm text-muted-foreground">No actions configured.</p>
            ) : (
              <div className="space-y-2">
                {hook.actions.map((action, index) => (
                  <div
                    key={index}
                    className={cn(
                      'border border-l-4 rounded-md p-3 bg-card',
                      actionAccentClass(action.type),
                    )}
                    data-testid={`overview-action-${index}`}
                  >
                    <p className="text-xs font-mono text-muted-foreground">
                      {index + 1}. {action.type}
                    </p>
                    <p className="text-sm mt-0.5">{actionSummary(action)}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Executions */}
        <div className="rounded-lg border flex flex-col" data-testid="overview-executions">
          <div className="shrink-0 flex items-center justify-between px-4 py-3 border-b">
            <p className="text-sm font-medium">Recent executions</p>
            <Button
              variant="outline"
              size="sm"
              className="h-7"
              onClick={() => void loadExecutions()}
              disabled={executionsLoading}
              data-testid="overview-executions-refresh"
            >
              <RefreshCw
                className={`h-3.5 w-3.5 mr-1 ${executionsLoading ? 'animate-spin' : ''}`}
              />
              Refresh
            </Button>
          </div>
          <div className="max-h-[320px] overflow-y-auto">
            {executionsLoading && executions.length === 0 ? (
              <div className="p-4 space-y-2">
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
              </div>
            ) : executions.length === 0 ? (
              <p
                className="text-sm text-muted-foreground p-6 text-center"
                data-testid="overview-executions-empty"
              >
                No executions yet. Run the hook to see history.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-8"></TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Trigger</TableHead>
                    <TableHead>Actions</TableHead>
                    <TableHead>Duration</TableHead>
                    <TableHead>Executed at</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {executions.map((ex) => {
                    const open = expandedId === ex.id;
                    return (
                      <Fragment key={ex.id}>
                        <TableRow
                          className="cursor-pointer"
                          data-testid={`execution-row-${ex.id}`}
                          onClick={() =>
                            setExpandedId((prev) => (prev === ex.id ? null : ex.id))
                          }
                        >
                          <TableCell className="w-8">
                            {open ? (
                              <ChevronDown className="h-4 w-4" />
                            ) : (
                              <ChevronRight className="h-4 w-4" />
                            )}
                          </TableCell>
                          <TableCell>
                            <ExecutionStatusBadge status={ex.status} />
                          </TableCell>
                          <TableCell className="text-sm capitalize">{ex.trigger_type}</TableCell>
                          <TableCell className="text-sm">{ex.actions_executed}</TableCell>
                          <TableCell className="text-sm text-muted-foreground">
                            {formatDurationMs(ex.duration_ms)}
                          </TableCell>
                          <TableCell className="text-sm text-muted-foreground">
                            {formatHookDate(ex.executed_at)}
                          </TableCell>
                        </TableRow>
                        {open && (
                          <TableRow data-testid={`execution-expand-${ex.id}`}>
                            <TableCell colSpan={6} className="bg-muted/30">
                              <div className="p-3 space-y-3 max-h-64 overflow-y-auto">
                                <div>
                                  <p className="text-xs font-medium text-muted-foreground mb-1">
                                    Execution id
                                  </p>
                                  <code className="text-xs font-mono">{ex.id}</code>
                                </div>
                                {ex.error_message && (
                                  <div>
                                    <p className="text-xs font-medium text-muted-foreground mb-1">
                                      Error
                                    </p>
                                    <pre
                                      className="text-xs text-destructive whitespace-pre-wrap font-mono"
                                      data-testid={`execution-error-${ex.id}`}
                                    >
                                      {ex.error_message}
                                    </pre>
                                  </div>
                                )}
                                <div>
                                  <p className="text-xs font-medium text-muted-foreground mb-1">
                                    Context
                                  </p>
                                  {ex.execution_context &&
                                  Object.keys(ex.execution_context).length > 0 ? (
                                    <pre
                                      className="text-xs font-mono bg-background border rounded p-2 overflow-x-auto"
                                      data-testid={`execution-context-${ex.id}`}
                                    >
                                      {JSON.stringify(ex.execution_context, null, 2)}
                                    </pre>
                                  ) : (
                                    <p
                                      className="text-xs text-muted-foreground"
                                      data-testid={`execution-context-empty-${ex.id}`}
                                    >
                                      No context
                                    </p>
                                  )}
                                </div>
                              </div>
                            </TableCell>
                          </TableRow>
                        )}
                      </Fragment>
                    );
                  })}
                </TableBody>
              </Table>
            )}
          </div>
        </div>
      </div>

      <DeleteHookDialog
        hook={hook}
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        onDeleted={() => {
          setDeleteOpen(false);
          navigate('/admin/hooks');
        }}
      />
    </div>
  );
}
