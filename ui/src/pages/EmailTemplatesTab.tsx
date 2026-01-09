import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { emailService, type EmailTemplate, type EmailLog } from '@/services/email.service';
import { DataTable, type Column } from '@/components/common/DataTable';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { formatDistanceToNow } from 'date-fns';
import { EmailTemplateEditDialog } from '@/components/common/EmailTemplateEditDialog';
import EmailLogList from '@/components/common/EmailLogList';
import EmailLogDetail from '@/components/common/EmailLogDetail';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';

const EmailTemplatesTab = () => {
    const [templateTypeFilter, setTemplateTypeFilter] = useState<string>('all');
    const [localeFilter, setLocaleFilter] = useState<string>('all');
    const [selectedTemplate, setSelectedTemplate] = useState<EmailTemplate | null>(null);
    const [selectedLog, setSelectedLog] = useState<EmailLog | null>(null);
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(10);

    const { data: allTemplates, isLoading } = useQuery({
        queryKey: ['email', 'templates', templateTypeFilter, localeFilter],
        queryFn: () =>
            emailService.listEmailTemplates({
                template_type: templateTypeFilter === 'all' ? undefined : templateTypeFilter,
                locale: localeFilter === 'all' ? undefined : localeFilter,
            }),
    });

    // Client-side pagination
    const paginatedData = useMemo(() => {
        if (!allTemplates) return [];
        const startIndex = (page - 1) * pageSize;
        return allTemplates.slice(startIndex, startIndex + pageSize);
    }, [allTemplates, page, pageSize]);

    const totalItems = allTemplates?.length || 0;

    const columns: Column<EmailTemplate>[] = [
        {
            header: 'Template Type',
            accessorKey: 'template_type',
            render: (template) => (
                <div className="flex items-center gap-2">
                    <span className="font-medium capitalize">
                        {template.template_type.replace(/_/g, ' ')}
                    </span>
                    {template.is_builtin && (
                        <Badge variant="secondary" className="text-xs">
                            Built-in
                        </Badge>
                    )}
                </div>
            ),
        },
        {
            header: 'Subject',
            accessorKey: 'subject',
            render: (template) => (
                <span className="text-sm text-muted-foreground line-clamp-1">
                    {template.subject}
                </span>
            ),
        },
        {
            header: 'Locale',
            accessorKey: 'locale',
            render: (template) => (
                <span className="uppercase text-sm font-mono">{template.locale}</span>
            ),
        },
        {
            header: 'Status',
            render: (template) => (
                <Badge variant={template.enabled ? 'default' : 'outline'}>
                    {template.enabled ? 'Enabled' : 'Disabled'}
                </Badge>
            ),
        },
        {
            header: 'Last Updated',
            accessorKey: 'updated_at',
            render: (template) => (
                <span className="text-sm text-muted-foreground">
                    {formatDistanceToNow(new Date(template.updated_at), { addSuffix: true })}
                </span>
            ),
        },
    ];

    return (
        <div className="space-y-8">
            {/* Email Templates Section */}
            <div className="space-y-4">
                <h3 className="text-lg font-semibold">Email Templates</h3>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
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

                        <Select
                            value={localeFilter}
                            onValueChange={(val) => {
                                setLocaleFilter(val);
                                setPage(1);
                            }}
                        >
                            <SelectTrigger className="w-[150px]">
                                <SelectValue placeholder="Filter by locale" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">All Locales</SelectItem>
                                <SelectItem value="en">English (en)</SelectItem>
                                <SelectItem value="es">Spanish (es)</SelectItem>
                                <SelectItem value="fr">French (fr)</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                </div>

                <DataTable
                    data={paginatedData}
                    columns={columns}
                    keyExtractor={(item) => item.id}
                    isLoading={isLoading}
                    totalItems={totalItems}
                    pagination={{
                        page,
                        pageSize,
                        onPageChange: setPage,
                        onPageSizeChange: (size) => {
                            setPageSize(size);
                            setPage(1);
                        },
                    }}
                    onRowClick={(template) => setSelectedTemplate(template)}
                    noDataMessage="No email templates found."
                />

                <EmailTemplateEditDialog
                    template={selectedTemplate}
                    open={!!selectedTemplate}
                    onOpenChange={(open) => !open && setSelectedTemplate(null)}
                />
            </div>

            {/* Separator */}
            <Separator />

            {/* Email Logs Section */}
            <div className="space-y-4">
                <h3 className="text-lg font-semibold">Email Logs</h3>
                <EmailLogList onLogClick={(log) => setSelectedLog(log)} />
                <EmailLogDetail
                    log={selectedLog}
                    open={!!selectedLog}
                    onOpenChange={(open) => !open && setSelectedLog(null)}
                />
            </div>
        </div>
    );
};

export default EmailTemplatesTab;

