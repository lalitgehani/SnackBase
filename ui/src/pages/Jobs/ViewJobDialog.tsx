import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
    AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { AlertCircle, RefreshCw, XCircle } from 'lucide-react';
import { useState } from 'react';
import { jobsService, type Job, type JobStatus } from '@/services/jobs.service';
import { useToast } from '@/hooks/use-toast';

interface ViewJobDialogProps {
    job: Job;
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onUpdated: () => void;
}

function statusVariant(status: JobStatus): 'default' | 'secondary' | 'destructive' | 'outline' {
    switch (status) {
        case 'pending': return 'outline';
        case 'running': return 'secondary';
        case 'completed': return 'default';
        case 'failed': return 'destructive';
        case 'retrying': return 'secondary';
        case 'dead': return 'destructive';
        default: return 'outline';
    }
}

function statusLabel(status: JobStatus): string {
    return status.charAt(0).toUpperCase() + status.slice(1);
}

function formatDate(dateStr: string | null): string {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleString();
}

export function ViewJobDialog({ job, open, onOpenChange, onUpdated }: ViewJobDialogProps) {
    const [retrying, setRetrying] = useState(false);
    const [cancelling, setCancelling] = useState(false);
    const { toast } = useToast();

    const handleRetry = async () => {
        setRetrying(true);
        try {
            await jobsService.retry(job.id);
            toast({ title: 'Job queued for retry' });
            onUpdated();
            onOpenChange(false);
        } catch {
            toast({ title: 'Failed to retry job', variant: 'destructive' });
        } finally {
            setRetrying(false);
        }
    };

    const handleCancel = async () => {
        setCancelling(true);
        try {
            await jobsService.cancel(job.id);
            toast({ title: 'Job cancelled' });
            onUpdated();
            onOpenChange(false);
        } catch {
            toast({ title: 'Failed to cancel job', variant: 'destructive' });
        } finally {
            setCancelling(false);
        }
    };

    const canRetry = job.status === 'dead' || job.status === 'failed' || job.status === 'retrying';
    const canCancel = job.status === 'pending';

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Job Details</DialogTitle>
                    <DialogDescription>
                        {job.handler} — {job.id}
                    </DialogDescription>
                </DialogHeader>

                <Tabs defaultValue="details">
                    <TabsList>
                        <TabsTrigger value="details">Details</TabsTrigger>
                        <TabsTrigger value="payload">Payload</TabsTrigger>
                    </TabsList>

                    <TabsContent value="details" className="space-y-4 mt-4">
                        {job.error_message && (
                            <Alert variant="destructive">
                                <AlertCircle className="h-4 w-4" />
                                <AlertDescription className="font-mono text-xs break-all">
                                    {job.error_message}
                                </AlertDescription>
                            </Alert>
                        )}

                        <div className="grid grid-cols-2 gap-3 text-sm">
                            <div>
                                <p className="text-muted-foreground text-xs mb-1">Status</p>
                                <Badge variant={statusVariant(job.status)}>
                                    {statusLabel(job.status)}
                                </Badge>
                            </div>
                            <div>
                                <p className="text-muted-foreground text-xs mb-1">Queue</p>
                                <Badge variant="outline">{job.queue}</Badge>
                            </div>
                            <div>
                                <p className="text-muted-foreground text-xs mb-1">Handler</p>
                                <p className="font-mono">{job.handler}</p>
                            </div>
                            <div>
                                <p className="text-muted-foreground text-xs mb-1">Priority</p>
                                <p>{job.priority}</p>
                            </div>
                            <div>
                                <p className="text-muted-foreground text-xs mb-1">Attempts</p>
                                <p>{job.attempt_number} / {job.max_retries}</p>
                            </div>
                            <div>
                                <p className="text-muted-foreground text-xs mb-1">Retry Delay</p>
                                <p>{job.retry_delay_seconds}s (exponential backoff)</p>
                            </div>
                            <div>
                                <p className="text-muted-foreground text-xs mb-1">Created At</p>
                                <p>{formatDate(job.created_at)}</p>
                            </div>
                            <div>
                                <p className="text-muted-foreground text-xs mb-1">Run At</p>
                                <p>{formatDate(job.run_at)}</p>
                            </div>
                            <div>
                                <p className="text-muted-foreground text-xs mb-1">Started At</p>
                                <p>{formatDate(job.started_at)}</p>
                            </div>
                            <div>
                                <p className="text-muted-foreground text-xs mb-1">Completed At</p>
                                <p>{formatDate(job.completed_at)}</p>
                            </div>
                            {job.failed_at && (
                                <div>
                                    <p className="text-muted-foreground text-xs mb-1">Failed At</p>
                                    <p>{formatDate(job.failed_at)}</p>
                                </div>
                            )}
                            {job.account_id && (
                                <div>
                                    <p className="text-muted-foreground text-xs mb-1">Account ID</p>
                                    <p className="font-mono text-xs">{job.account_id}</p>
                                </div>
                            )}
                        </div>

                        <div className="flex gap-2 pt-2">
                            {canRetry && (
                                <AlertDialog>
                                    <AlertDialogTrigger asChild>
                                        <Button variant="outline" size="sm" disabled={retrying}>
                                            <RefreshCw className="h-4 w-4 mr-2" />
                                            Retry Job
                                        </Button>
                                    </AlertDialogTrigger>
                                    <AlertDialogContent>
                                        <AlertDialogHeader>
                                            <AlertDialogTitle>Retry Job</AlertDialogTitle>
                                            <AlertDialogDescription>
                                                This will reset the job to pending and re-queue it for execution. Are you sure?
                                            </AlertDialogDescription>
                                        </AlertDialogHeader>
                                        <AlertDialogFooter>
                                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                                            <AlertDialogAction onClick={handleRetry} disabled={retrying}>
                                                Retry
                                            </AlertDialogAction>
                                        </AlertDialogFooter>
                                    </AlertDialogContent>
                                </AlertDialog>
                            )}
                            {canCancel && (
                                <AlertDialog>
                                    <AlertDialogTrigger asChild>
                                        <Button variant="destructive" size="sm" disabled={cancelling}>
                                            <XCircle className="h-4 w-4 mr-2" />
                                            Cancel Job
                                        </Button>
                                    </AlertDialogTrigger>
                                    <AlertDialogContent>
                                        <AlertDialogHeader>
                                            <AlertDialogTitle>Cancel Job</AlertDialogTitle>
                                            <AlertDialogDescription>
                                                This will permanently delete the pending job. This cannot be undone. Are you sure?
                                            </AlertDialogDescription>
                                        </AlertDialogHeader>
                                        <AlertDialogFooter>
                                            <AlertDialogCancel>Keep Job</AlertDialogCancel>
                                            <AlertDialogAction
                                                onClick={handleCancel}
                                                disabled={cancelling}
                                                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                            >
                                                Cancel Job
                                            </AlertDialogAction>
                                        </AlertDialogFooter>
                                    </AlertDialogContent>
                                </AlertDialog>
                            )}
                        </div>
                    </TabsContent>

                    <TabsContent value="payload" className="mt-4">
                        <div className="bg-muted rounded-md p-4 overflow-auto max-h-96">
                            <pre className="text-xs font-mono whitespace-pre-wrap break-all">
                                {JSON.stringify(job.payload, null, 2)}
                            </pre>
                        </div>
                    </TabsContent>
                </Tabs>
            </DialogContent>
        </Dialog>
    );
}
