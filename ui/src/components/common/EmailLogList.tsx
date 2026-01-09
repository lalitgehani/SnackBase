import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { emailService, type EmailLog } from '@/services/email.service';
import { DataTable, type Column } from '@/components/common/DataTable';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { formatDistanceToNow } from 'date-fns';

interface EmailLogListProps {
    onLogClick: (log: EmailLog) => void;
}

const EmailLogList = ({ onLogClick }: EmailLogListProps) => {
    const [statusFilter, setStatusFilter] = useState<string>('all');
    const [templateTypeFilter, setTemplateTypeFilter] = useState<string>('all');
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(25);

    const { data, isLoading } = useQuery({
        queryKey: ['email', 'logs', statusFilter, templateTypeFilter, page, pageSize],
        queryFn: () =>
            emailService.listEmailLogs({
                status_filter: statusFilter === 'all' ? undefined : statusFilter,
                template_type: templateTypeFilter === 'all' ? undefined : templateTypeFilter,
                page,
                page_size: pageSize,
            }),
        refetchInterval: 30000, // Auto-refresh every 30 seconds
    });

    const columns: Column<EmailLog>[] = [
        {
            header: 'Recipient',
            accessorKey: 'recipient_email',
            render: (log) => (
                <span className="font-medium text-sm">{log.recipient_email}</span>
            ),
        },
        {
            header: 'Template Type',
            accessorKey: 'template_type',
            render: (log) => (
                <span className="text-sm capitalize">
                    {log.template_type.replace(/_/g, ' ')}
                </span>
            ),
        },
        {
            header: 'Provider',
            accessorKey: 'provider',
            render: (log) => (
                <span className="text-sm uppercase font-mono">{log.provider}</span>
            ),
        },
        {
            header: 'Status',
            render: (log) => {
                const variant =
                    log.status === 'sent'
                        ? 'default'
                        : log.status === 'failed'
                            ? 'destructive'
                            : 'secondary';
                return (
                    <Badge variant={variant} className="capitalize">
                        {log.status}
                    </Badge>
                );
            },
        },
        {
            header: 'Sent At',
            accessorKey: 'sent_at',
            render: (log) => (
                <span className="text-sm text-muted-foreground">
                    {formatDistanceToNow(new Date(log.sent_at), { addSuffix: true })}
                </span>
            ),
        },
    ];

    return (
        <div className="space-y-4">
            <div className="flex items-center gap-2">
                <Select
                    value={statusFilter}
                    onValueChange={(val) => {
                        setStatusFilter(val);
                        setPage(1);
                    }}
                >
                    <SelectTrigger className="w-[150px]">
                        <SelectValue placeholder="Filter by status" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all">All Status</SelectItem>
                        <SelectItem value="sent">Sent</SelectItem>
                        <SelectItem value="failed">Failed</SelectItem>
                        <SelectItem value="pending">Pending</SelectItem>
                    </SelectContent>
                </Select>

                <Select
                    value={templateTypeFilter}
                    onValueChange={(val) => {
                        setTemplateTypeFilter(val);
                        setPage(1);
                    }}
                >
                    <SelectTrigger className="w-[200px]">
                        <SelectValue placeholder="Filter by type" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all">All Types</SelectItem>
                        <SelectItem value="email_verification">Email Verification</SelectItem>
                        <SelectItem value="password_reset">Password Reset</SelectItem>
                        <SelectItem value="invitation">Invitation</SelectItem>
                    </SelectContent>
                </Select>
            </div>

            <DataTable
                data={data?.logs || []}
                columns={columns}
                keyExtractor={(item) => item.id}
                isLoading={isLoading}
                totalItems={data?.total || 0}
                pagination={{
                    page,
                    pageSize,
                    onPageChange: setPage,
                    onPageSizeChange: (size) => {
                        setPageSize(size);
                        setPage(1);
                    },
                }}
                onRowClick={onLogClick}
                noDataMessage="No email logs found."
            />
        </div>
    );
};

export default EmailLogList;
