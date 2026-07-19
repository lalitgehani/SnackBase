import { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { AppDialog } from '@/components/common/AppDialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';
import { handleApiError } from '@/lib/api';
import { emailService, type EmailTemplate, type EmailTemplateUpdate } from '@/services/email.service';
import { adminService, type Configuration } from '@/services/admin.service';
import { useQuery } from '@tanstack/react-query';
import { Loader2, Send, CheckCircle2, XCircle } from 'lucide-react';

interface EmailTemplateEditDialogProps {
    template: EmailTemplate | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

// Hardcoded template variables per template type
const TEMPLATE_VARIABLES: Record<string, string[]> = {
    email_verification: [
        'app_name',
        'app_url',
        'user_name',
        'user_email',
        'verification_url',
        'token',
        'expires_at',
    ],
    password_reset: [
        'app_name',
        'app_url',
        'user_name',
        'user_email',
        'reset_url',
        'token',
        'expires_at',
    ],
    invitation: [
        'app_name',
        'app_url',
        'user_name',
        'user_email',
        'invitation_url',
        'token',
        'account_name',
        'invited_by',
        'expires_at',
    ],
};

export const EmailTemplateEditDialog = ({
    template,
    open,
    onOpenChange,
}: EmailTemplateEditDialogProps) => {
    const [formData, setFormData] = useState<EmailTemplateUpdate>({});
    const [testEmail, setTestEmail] = useState('');
    const [selectedProvider, setSelectedProvider] = useState<string>('auto');
    const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
    const [previewHtml, setPreviewHtml] = useState<string>('');
    const [previewText, setPreviewText] = useState<string>('');
    const [previewLoading, setPreviewLoading] = useState(false);
    /** Which body format is shown in the editor / preview */
    const [bodyFormat, setBodyFormat] = useState<'html' | 'text'>('html');

    const queryClient = useQueryClient();
    const { toast } = useToast();

    useEffect(() => {
        if (template) {
            setFormData({
                subject: template.subject,
                html_body: template.html_body,
                text_body: template.text_body,
                enabled: template.enabled,
            });
        }
    }, [template]);

    // Fetch enabled email providers (system and account)
    const { data: providers } = useQuery({
        queryKey: ['providers', template?.account_id],
        queryFn: async () => {
            const systemConfigs = await adminService.getSystemConfigs('email_providers');
            let configs = [...systemConfigs];

            if (template?.account_id && template.account_id !== '00000000-0000-0000-0000-000000000000') {
                const accountConfigs = await adminService.getAccountConfigs(template.account_id, 'email_providers');
                configs = [...configs, ...accountConfigs];
            }

            // Filter enabled only and deduplicate by provider_name
            const uniqueProviders = new Map<string, Configuration>();
            configs.filter(c => c.enabled).forEach(c => {
                if (!uniqueProviders.has(c.provider_name)) {
                    uniqueProviders.set(c.provider_name, c);
                }
            });
            return Array.from(uniqueProviders.values());
        },
        enabled: !!template,
    });

    const updateMutation = useMutation({
        mutationFn: (data: EmailTemplateUpdate) =>
            emailService.updateEmailTemplate(template!.id, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['email', 'templates'] });
            toast({
                title: 'Template Updated',
                description: 'Email template has been updated successfully.',
            });
            onOpenChange(false);
        },
        onError: (error: unknown) => {
            toast({
                title: 'Error',
                description: handleApiError(error) || 'Failed to update template.',
                variant: 'destructive',
            });
        },
    });

    const testEmailMutation = useMutation({
        mutationFn: (recipient: string) =>
            emailService.sendTestEmail(template!.id, {
                recipient_email: recipient,
                variables: {},
                provider: selectedProvider === 'auto' ? undefined : selectedProvider,
            }),
        onSuccess: (data) => {
            setTestEmail('');
            setTestResult({ success: true, message: data.message });
            // Clear message after 5 seconds
            setTimeout(() => setTestResult(null), 5000);
        },
        onError: (error: unknown) => {
            setTestResult({
                success: false,
                message: handleApiError(error) || 'Failed to send test email.'
            });
        },
    });

    const handleSave = () => {
        updateMutation.mutate(formData);
    };

    const handleSendTest = () => {
        if (!testEmail) {
            setTestResult({
                success: false,
                message: 'Please enter a recipient email address.'
            });
            return;
        }
        setTestResult(null);
        testEmailMutation.mutate(testEmail);
    };

    // Preview Logic
    const handlePreview = async (overrideData?: Partial<EmailTemplateUpdate>) => {
        if (!template) return;

        setPreviewLoading(true);
        try {
            // Create dummy variables for preview based on template type
            const variables: Record<string, string> = {};
            const keys = TEMPLATE_VARIABLES[template.template_type] || [];

            keys.forEach(key => {
                // Generate a dummy value for each variable
                const readableKey = key.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
                variables[key] = `[${readableKey}]`;
            });

            // If specific variables make sense to have realistic defaults, override them
            if (keys.includes('app_name')) variables['app_name'] = 'SnackBase';
            if (keys.includes('app_url')) variables['app_url'] = 'http://localhost:3000';
            if (keys.includes('user_name')) variables['user_name'] = 'John Doe';
            if (keys.includes('user_email')) variables['user_email'] = 'john@example.com';

            const dataToRender = overrideData || formData;

            const response = await emailService.renderEmailTemplate({
                template_type: template.template_type,
                variables,
                locale: template.locale,
                account_id: template.account_id,
                subject: dataToRender.subject || template.subject,
                html_body: dataToRender.html_body || template.html_body,
                text_body: dataToRender.text_body || template.text_body,
            });

            setPreviewHtml(response.html_body);
            setPreviewText(response.text_body);
        } catch {
            toast({
                title: 'Preview Failed',
                description: 'Could not generate preview.',
                variant: 'destructive',
            });
        } finally {
            setPreviewLoading(false);
        }
    };

    useEffect(() => {
        if (template && open) {
            const initialData = {
                subject: template.subject,
                html_body: template.html_body,
                text_body: template.text_body,
                enabled: template.enabled,
            };
            setFormData(initialData);
            setBodyFormat('html');
            setPreviewHtml('');
            setPreviewText('');
            handlePreview(initialData);
        }
        // Intentionally only re-run when dialog opens or template identity changes.
        // eslint-disable-next-line react-hooks/exhaustive-deps -- avoid re-preview loop while editing form fields
    }, [template, open]);

    const bodyField = bodyFormat === 'html' ? 'html_body' : 'text_body';

    const [focusedField, setFocusedField] = useState<'subject' | 'html_body' | 'text_body' | null>('subject');
    const [cursorPosition, setCursorPosition] = useState<number | null>(null);

    const handleBodyFormatChange = (value: string) => {
        const next = value === 'text' ? 'text' : 'html';
        setBodyFormat(next);
        setFocusedField(next === 'html' ? 'html_body' : 'text_body');
        setCursorPosition(null);
    };

    const handleInputFocus = (field: 'subject' | 'html_body' | 'text_body') => {
        setFocusedField(field);
    };

    const handleInputSelect = (e: React.SyntheticEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        setCursorPosition(e.currentTarget.selectionStart);
    };

    const insertVariable = (variable: string) => {
        const varText = `{{${variable}}}`;

        setFormData((prev) => {
            const field = focusedField || 'subject';
            const currentValue = prev[field] || '';

            // If we have a cursor position and it's for the current field, insert there
            // Otherwise append to end
            const insertPos = cursorPosition !== null ? cursorPosition : currentValue.length;

            const newValue =
                currentValue.slice(0, insertPos) +
                varText +
                currentValue.slice(insertPos);

            // Update cursor position to be after inserted text
            setCursorPosition(insertPos + varText.length);

            return {
                ...prev,
                [field]: newValue,
            };
        });
    };

    if (!template) return null;

    const availableVariables = TEMPLATE_VARIABLES[template.template_type] || [];

    return (
        <AppDialog
            open={open}
            onOpenChange={onOpenChange}
            title={`Edit Template: ${template.template_type} (${template.locale})`}
            className="sm:max-w-5xl lg:max-w-6xl w-[calc(100%-2rem)] md:h-[90vh]"
            bodyClassName="flex flex-col px-6 py-4 min-h-0 overflow-y-auto md:overflow-hidden"
            footer={
                <>
                    <div className="mr-auto flex items-center">
                        {template.is_builtin && (
                            <span className="text-xs text-muted-foreground bg-secondary px-2 py-1 rounded">
                                Built-in Template
                            </span>
                        )}
                        {testResult && (
                            <span className={`ml-4 text-sm flex items-center ${testResult.success ? 'text-green-600' : 'text-destructive'}`}>
                                {testResult.success ? (
                                    <CheckCircle2 className="h-4 w-4 mr-1" />
                                ) : (
                                    <XCircle className="h-4 w-4 mr-1" />
                                )}
                                {testResult.message}
                            </span>
                        )}
                    </div>
                    <Button variant="outline" onClick={() => onOpenChange(false)}>
                        Cancel
                    </Button>
                    <Button onClick={handleSave} disabled={updateMutation.isPending}>
                        {updateMutation.isPending ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Saving...
                            </>
                        ) : (
                            'Save Changes'
                        )}
                    </Button>
                </>
            }
        >
            <div className="flex flex-col flex-1 min-h-0 gap-4">
                {/* Side-by-side editor + preview — fills dialog body height on md+ */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 md:flex-1 md:min-h-0">
                    {/* Left: form fields (scroll independently on md+) */}
                    <div className="min-w-0 md:min-h-0 md:overflow-y-auto md:flex md:flex-col space-y-4 md:pr-1">
                        {/* Enabled Toggle */}
                        <div className="flex items-center justify-between">
                            <Label htmlFor="enabled">Enabled</Label>
                            <Switch
                                id="enabled"
                                checked={formData.enabled ?? template.enabled}
                                onCheckedChange={(checked) =>
                                    setFormData((prev) => ({ ...prev, enabled: checked }))
                                }
                            />
                        </div>

                        {/* Variable Selector */}
                        {availableVariables.length > 0 && (
                            <div className="space-y-2">
                                <Label>Insert Variable</Label>
                                <Select onValueChange={insertVariable}>
                                    <SelectTrigger>
                                        <SelectValue placeholder={`Insert into ${focusedField || 'subject'}`} />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {availableVariables.map((variable) => (
                                            <SelectItem key={variable} value={variable}>
                                                {`{{${variable}}}`}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        )}

                        {/* Subject */}
                        <div className="space-y-2">
                            <Label htmlFor="subject">Subject</Label>
                            <Input
                                id="subject"
                                value={formData.subject ?? template.subject}
                                onChange={(e) =>
                                    setFormData((prev) => ({ ...prev, subject: e.target.value }))
                                }
                                onFocus={() => handleInputFocus('subject')}
                                onSelect={handleInputSelect}
                                placeholder="Email subject line"
                            />
                        </div>

                        {/* Body — HTML or plain text via format selector */}
                        <div className="space-y-2 flex flex-col flex-1 min-h-0">
                            <div className="flex items-center justify-between gap-3">
                                <Label htmlFor="body_editor">Body</Label>
                                <Select value={bodyFormat} onValueChange={handleBodyFormatChange}>
                                    <SelectTrigger id="body_format" className="w-[140px] h-8">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="html">HTML</SelectItem>
                                        <SelectItem value="text">Plain text</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                            <Textarea
                                id="body_editor"
                                value={
                                    bodyFormat === 'html'
                                        ? (formData.html_body ?? template.html_body)
                                        : (formData.text_body ?? template.text_body)
                                }
                                onChange={(e) =>
                                    setFormData((prev) => ({
                                        ...prev,
                                        [bodyField]: e.target.value,
                                    }))
                                }
                                onFocus={() => handleInputFocus(bodyField)}
                                onSelect={handleInputSelect}
                                placeholder={
                                    bodyFormat === 'html'
                                        ? 'HTML email body'
                                        : 'Plain text email body (fallback for clients that do not render HTML)'
                                }
                                className="font-mono text-sm field-sizing-fixed resize-y min-h-[280px] h-[48vh] md:h-auto md:min-h-0 md:flex-1"
                            />
                            <p className="text-xs text-muted-foreground">
                                {bodyFormat === 'html'
                                    ? 'Rich HTML version shown in most email clients.'
                                    : 'Plain-text fallback sent with every email for clients that do not render HTML.'}
                            </p>
                        </div>
                    </div>

                    {/* Right: full-height live preview (matches selected body format) */}
                    <div className="min-w-0 min-h-[360px] md:min-h-0 flex flex-col gap-2">
                        <div className="flex justify-between items-center gap-2 shrink-0">
                            <div className="flex items-center gap-2">
                                <Label>
                                    Preview
                                    <span className="ml-1.5 font-normal text-muted-foreground">
                                        ({bodyFormat === 'html' ? 'HTML' : 'Plain text'})
                                    </span>
                                </Label>
                                {previewLoading && (
                                    <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
                                )}
                            </div>
                            <Button
                                size="sm"
                                variant="secondary"
                                onClick={() => handlePreview()}
                                disabled={previewLoading}
                            >
                                Refresh Preview
                            </Button>
                        </div>
                        <div className="rounded-md border overflow-hidden bg-muted/30 flex-1 min-h-0 relative">
                            {previewLoading && !previewHtml && !previewText ? (
                                <div className="absolute inset-0 flex items-center justify-center text-muted-foreground gap-2">
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                    Generating preview…
                                </div>
                            ) : bodyFormat === 'html' ? (
                                previewHtml ? (
                                    // Intentional light email canvas (theme exception — HTML email previews use a white background).
                                    <iframe
                                        srcDoc={previewHtml}
                                        title="Email HTML Preview"
                                        className="absolute inset-0 w-full h-full border-0 bg-white"
                                        sandbox="allow-same-origin"
                                    />
                                ) : (
                                    <div className="absolute inset-0 flex items-center justify-center text-muted-foreground text-sm px-4 text-center">
                                        Click Refresh Preview to render the email
                                    </div>
                                )
                            ) : previewText ? (
                                <pre className="absolute inset-0 m-0 p-4 overflow-auto whitespace-pre-wrap break-words font-mono text-sm text-foreground bg-background">
                                    {previewText}
                                </pre>
                            ) : (
                                <div className="absolute inset-0 flex items-center justify-center text-muted-foreground text-sm px-4 text-center">
                                    Click Refresh Preview to render the email
                                </div>
                            )}
                        </div>
                        <p className="text-xs text-muted-foreground shrink-0">
                            Preview uses sample values for template variables.
                        </p>
                    </div>
                </div>

                {/* Test Email — pinned full width below editor/preview */}
                <div className="space-y-2 border-t pt-4 shrink-0">
                    <Label>Send Test Email</Label>
                    <div className="grid grid-cols-1 sm:grid-cols-[1fr_2fr_auto] gap-2 items-end">
                        <div className="space-y-2">
                            <Label htmlFor="provider-select" className="text-xs text-muted-foreground">Provider</Label>
                            <Select value={selectedProvider} onValueChange={setSelectedProvider}>
                                <SelectTrigger id="provider-select">
                                    <SelectValue placeholder="Automatic" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="auto">Automatic (Default)</SelectItem>
                                    {providers?.map((provider) => (
                                        <SelectItem key={provider.provider_name} value={provider.provider_name}>
                                            {provider.display_name || provider.provider_name}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="test_email" className="text-xs text-muted-foreground">Recipient</Label>
                            <Input
                                id="test_email"
                                type="email"
                                value={testEmail}
                                onChange={(e) => setTestEmail(e.target.value)}
                                placeholder="recipient@example.com"
                            />
                        </div>
                        <Button
                            onClick={handleSendTest}
                            disabled={testEmailMutation.isPending}
                            variant="outline"
                            className="mb-0.5"
                        >
                            {testEmailMutation.isPending ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                                <Send className="h-4 w-4" />
                            )}
                            <span className="ml-2">Send</span>
                        </Button>
                    </div>
                </div>
            </div>
        </AppDialog>
    );
};
