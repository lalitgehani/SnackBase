import type { ReactNode } from 'react';
import { AppDialog } from '@/components/common/AppDialog';
import { Badge } from '@/components/ui/badge';
import type { EmailLog } from '@/services/email.service';
import { format } from 'date-fns';

interface EmailLogDetailProps {
    log: EmailLog | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

function DetailField({
    label,
    children,
    className,
}: {
    label: string;
    children: ReactNode;
    className?: string;
}) {
    return (
        <div className={className}>
            <div className="text-sm font-medium text-muted-foreground">{label}</div>
            <div className="mt-1 text-sm break-words">{children}</div>
        </div>
    );
}

const EmailLogDetail = ({ log, open, onOpenChange }: EmailLogDetailProps) => {
    if (!log) return null;

    const statusVariant =
        log.status === 'sent'
            ? 'default'
            : log.status === 'failed'
                ? 'destructive'
                : 'secondary';

    const providerLabel =
        !log.provider || log.provider.toLowerCase() === 'unknown'
            ? '—'
            : log.provider;

    return (
        <AppDialog
            open={open}
            onOpenChange={onOpenChange}
            title="Email Log Details"
            className="sm:max-w-2xl"
            bodyClassName="px-6 py-4 overflow-y-auto min-h-0"
        >
            <div className="space-y-5">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4">
                    <DetailField label="Status">
                        <Badge variant={statusVariant} className="capitalize">
                            {log.status}
                        </Badge>
                    </DetailField>

                    <DetailField label="Provider">
                        <span className="font-mono text-sm uppercase tracking-wide">
                            {providerLabel}
                        </span>
                    </DetailField>

                    <DetailField label="Recipient">
                        <span className="break-all">{log.recipient_email}</span>
                    </DetailField>

                    <DetailField label="Template Type">
                        <span className="capitalize">
                            {log.template_type.replace(/_/g, ' ')}
                        </span>
                    </DetailField>

                    <DetailField label="Sent At">
                        {format(new Date(log.sent_at), 'PPpp')}
                    </DetailField>

                    <DetailField label="Log ID">
                        <code className="block font-mono text-xs leading-relaxed break-all select-all">
                            {log.id}
                        </code>
                    </DetailField>
                </div>

                {log.error_message && (
                    <div>
                        <div className="text-sm font-medium text-destructive">
                            Error Message
                        </div>
                        <div className="mt-1.5 p-3 bg-destructive/10 border border-destructive/20 rounded-md">
                            <p className="text-sm text-destructive whitespace-pre-wrap break-words">
                                {log.error_message}
                            </p>
                        </div>
                    </div>
                )}

                {log.variables && Object.keys(log.variables).length > 0 && (
                    <div>
                        <div className="text-sm font-medium text-muted-foreground mb-1.5">
                            Template Variables
                        </div>
                        <div className="rounded-md border bg-muted/40 overflow-hidden">
                            <dl className="divide-y divide-border">
                                {Object.entries(log.variables).map(([key, value]) => (
                                    <div
                                        key={key}
                                        className="grid grid-cols-1 sm:grid-cols-[minmax(7rem,10rem)_1fr] gap-1 sm:gap-3 px-3 py-2.5"
                                    >
                                        <dt className="text-sm font-medium text-foreground shrink-0">
                                            {key}
                                        </dt>
                                        <dd className="text-sm text-muted-foreground font-mono break-all min-w-0">
                                            {value === '' || value == null ? (
                                                <span className="italic text-muted-foreground/70">
                                                    (empty)
                                                </span>
                                            ) : (
                                                value
                                            )}
                                        </dd>
                                    </div>
                                ))}
                            </dl>
                        </div>
                    </div>
                )}
            </div>
        </AppDialog>
    );
};

export default EmailLogDetail;
