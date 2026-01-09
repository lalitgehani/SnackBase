import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import type { EmailLog } from '@/services/email.service';
import { format } from 'date-fns';

interface EmailLogDetailProps {
    log: EmailLog | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

const EmailLogDetail = ({ log, open, onOpenChange }: EmailLogDetailProps) => {
    if (!log) return null;

    const statusVariant =
        log.status === 'sent'
            ? 'default'
            : log.status === 'failed'
                ? 'destructive'
                : 'secondary';

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Email Log Details</DialogTitle>
                </DialogHeader>

                <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="text-sm font-medium text-muted-foreground">
                                Status
                            </label>
                            <div className="mt-1">
                                <Badge variant={statusVariant} className="capitalize">
                                    {log.status}
                                </Badge>
                            </div>
                        </div>

                        <div>
                            <label className="text-sm font-medium text-muted-foreground">
                                Provider
                            </label>
                            <p className="mt-1 text-sm font-mono uppercase">{log.provider}</p>
                        </div>

                        <div>
                            <label className="text-sm font-medium text-muted-foreground">
                                Recipient
                            </label>
                            <p className="mt-1 text-sm">{log.recipient_email}</p>
                        </div>

                        <div>
                            <label className="text-sm font-medium text-muted-foreground">
                                Template Type
                            </label>
                            <p className="mt-1 text-sm capitalize">
                                {log.template_type.replace(/_/g, ' ')}
                            </p>
                        </div>

                        <div>
                            <label className="text-sm font-medium text-muted-foreground">
                                Sent At
                            </label>
                            <p className="mt-1 text-sm">
                                {format(new Date(log.sent_at), 'PPpp')}
                            </p>
                        </div>

                        <div>
                            <label className="text-sm font-medium text-muted-foreground">
                                Log ID
                            </label>
                            <p className="mt-1 font-mono text-xs">{log.id}</p>
                        </div>
                    </div>

                    {log.error_message && (
                        <div>
                            <label className="text-sm font-medium text-destructive">
                                Error Message
                            </label>
                            <div className="mt-1 p-3 bg-destructive/10 border border-destructive/20 rounded-md">
                                <p className="text-sm text-destructive whitespace-pre-wrap">
                                    {log.error_message}
                                </p>
                            </div>
                        </div>
                    )}

                    {log.variables && Object.keys(log.variables).length > 0 && (
                        <div>
                            <label className="text-sm font-medium text-muted-foreground">
                                Template Variables
                            </label>
                            <div className="mt-1 p-3 bg-muted rounded-md">
                                <dl className="space-y-2">
                                    {Object.entries(log.variables).map(([key, value]) => (
                                        <div key={key} className="flex gap-2">
                                            <dt className="text-sm font-medium min-w-[120px]">
                                                {key}:
                                            </dt>
                                            <dd className="text-sm text-muted-foreground">
                                                {value}
                                            </dd>
                                        </div>
                                    ))}
                                </dl>
                            </div>
                        </div>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    );
};

export default EmailLogDetail;
