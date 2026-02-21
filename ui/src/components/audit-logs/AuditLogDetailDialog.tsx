/**
 * Audit log detail dialog component
 */

import { AppDialog } from '@/components/common/AppDialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import type { AuditLogItem } from '@/services/audit.service';
import { format } from 'date-fns';
import { Shield, User, Globe, FileText, Database } from 'lucide-react';

interface AuditLogDetailDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    log: AuditLogItem | null;
}

const DetailItem = ({ label, value, icon: Icon, mono = false }: { label: string; value: unknown; icon?: React.ElementType; mono?: boolean }) => (
    <div className="flex flex-col space-y-1 py-2">
        <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
            {Icon && <Icon className="h-4 w-4" />}
            {label}
        </div>
        <div className={`text-sm break-all font-medium ${mono ? 'font-mono' : ''}`}>
            {value !== null && value !== undefined ? String(value) : <span className="text-muted-foreground italic">NULL</span>}
        </div>
    </div>
);

export default function AuditLogDetailDialog({
    open,
    onOpenChange,
    log,
}: AuditLogDetailDialogProps) {
    if (!log) return null;

    return (
        <AppDialog
            open={open}
            onOpenChange={onOpenChange}
            title={`Audit Log Entry #${log.id}`}
            description="Full details of the captured data change"
            className="max-w-2xl"
        >
            <ScrollArea className="pr-4 h-full">
                <div className="space-y-6">
                    {/* Summary Section */}
                    <div className="grid grid-cols-2 gap-4">
                        <DetailItem label="Operation" value={log.operation} icon={FileText} />
                        <DetailItem label="Timestamp" value={format(new Date(log.occurred_at), 'yyyy-MM-dd HH:mm:ss (O)')} icon={Globe} />
                        <DetailItem label="Collection" value={log.table_name} icon={Database} />
                        <DetailItem label="Column" value={log.column_name} icon={Database} />
                    </div>

                    <Separator />

                    {/* Record Details */}
                    <div>
                        <DetailItem label="Record ID" value={log.record_id} icon={FileText} mono />
                    </div>

                    {/* Value Change */}
                    <div className="grid grid-cols-2 gap-4 bg-muted/50 p-4 rounded-lg">
                        <div>
                            <h4 className="text-xs font-bold uppercase text-muted-foreground mb-2">Old Value</h4>
                            <pre className="text-xs whitespace-pre-wrap break-all p-2 bg-background rounded border min-h-10">
                                {log.old_value !== null ? String(log.old_value) : 'NULL'}
                            </pre>
                        </div>
                        <div>
                            <h4 className="text-xs font-bold uppercase text-muted-foreground mb-2">New Value</h4>
                            <pre className="text-xs whitespace-pre-wrap break-all p-2 bg-background rounded border min-h-10">
                                {log.new_value !== null ? String(log.new_value) : 'NULL'}
                            </pre>
                        </div>
                    </div>

                    <Separator />

                    {/* User Context */}
                    <div className="grid grid-cols-2 gap-4">
                        <DetailItem label="User Name" value={log.user_name} icon={User} />
                        <DetailItem label="User Email" value={log.user_email} icon={User} />
                        <DetailItem label="User ID" value={log.user_id} icon={User} mono />
                        <DetailItem label="IP Address" value={log.ip_address} icon={Globe} />
                    </div>

                    <Separator />

                    {/* Request Metadata */}
                    <div>
                        <DetailItem label="User Agent" value={log.user_agent} />
                        <DetailItem label="Request ID" value={log.request_id} mono />
                    </div>

                    <Separator />

                    {/* Integrity Chain */}
                    <div className="space-y-4">
                        <h3 className="flex items-center gap-2 text-sm font-bold uppercase text-primary">
                            <Shield className="h-4 w-4" />
                            Integrity Chain (Blockchain Style)
                        </h3>
                        <div className="space-y-2">
                            <DetailItem label="Current Checksum (SHA-256)" value={log.checksum} mono />
                            <DetailItem label="Previous Hash" value={log.previous_hash} mono />
                        </div>
                        {(log.es_username || log.es_reason) && (
                            <div className="mt-4 p-4 bg-primary/5 rounded border border-primary/20">
                                <h4 className="text-xs font-bold uppercase text-primary mb-2">Electronic Signature (CFR Part 11)</h4>
                                <div className="grid grid-cols-2 gap-2 text-sm">
                                    <div><span className="text-muted-foreground">Signer:</span> {log.es_username}</div>
                                    <div><span className="text-muted-foreground">Reason:</span> {log.es_reason}</div>
                                    {log.es_timestamp && (
                                        <div className="col-span-2">
                                            <span className="text-muted-foreground">Timestamp:</span> {format(new Date(log.es_timestamp), 'yyyy-MM-dd HH:mm:ss')}
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Extra Metadata */}
                    {log.extra_metadata && Object.keys(log.extra_metadata).length > 0 && (
                        <>
                            <Separator />
                            <div>
                                <h4 className="text-xs font-bold uppercase text-muted-foreground mb-2">Additional Metadata</h4>
                                <pre className="text-xs p-2 bg-muted rounded overflow-auto">
                                    {JSON.stringify(log.extra_metadata, null, 2)}
                                </pre>
                            </div>
                        </>
                    )}
                </div>
            </ScrollArea>
        </AppDialog>
    );
}
