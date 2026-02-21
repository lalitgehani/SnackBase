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
    const [previewLoading, setPreviewLoading] = useState(false);

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
        onError: (error: any) => {
            toast({
                title: 'Error',
                description: error.response?.data?.detail || 'Failed to update template.',
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
        onError: (error: any) => {
            setTestResult({
                success: false,
                message: error.response?.data?.detail || 'Failed to send test email.'
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
        } catch (error: any) {
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
            setPreviewHtml(''); // Clear old preview
            handlePreview(initialData); // Use new data immediately
        }
    }, [template, open]);

    const [focusedField, setFocusedField] = useState<'subject' | 'html_body' | 'text_body' | null>('subject');
    const [cursorPosition, setCursorPosition] = useState<number | null>(null);

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
            className="max-w-2xl"
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
            <div className="space-y-4">
                {/* Enabled Toggle & Vars */}
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

                {/* HTML Body */}
                <div className="space-y-2">
                    <Label htmlFor="html_body">HTML Body</Label>
                    <Textarea
                        id="html_body"
                        value={formData.html_body ?? template.html_body}
                        onChange={(e) =>
                            setFormData((prev) => ({ ...prev, html_body: e.target.value }))
                        }
                        onFocus={() => handleInputFocus('html_body')}
                        onSelect={handleInputSelect}
                        placeholder="HTML email body"
                        className="font-mono text-sm resize-none min-h-[200px]"
                    />
                </div>

                {/* Text Body */}
                <div className="space-y-2">
                    <Label htmlFor="text_body">Text Body</Label>
                    <Textarea
                        id="text_body"
                        value={formData.text_body ?? template.text_body}
                        onChange={(e) =>
                            setFormData((prev) => ({ ...prev, text_body: e.target.value }))
                        }
                        onFocus={() => handleInputFocus('text_body')}
                        onSelect={handleInputSelect}
                        placeholder="Plain text email body"
                        className="font-mono text-sm min-h-[100px]"
                    />
                </div>

                {/* Preview */}
                <div className="space-y-2">
                    <div className="flex justify-between items-center">
                        <Label>Preview</Label>
                        <Button size="sm" variant="secondary" onClick={() => handlePreview()} disabled={previewLoading}>
                            {previewLoading ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : null}
                            Refresh Preview
                        </Button>
                    </div>
                    <div className="rounded-md border overflow-hidden bg-gray-50 dark:bg-gray-900" style={{ height: '300px' }}>
                        {previewHtml ? (
                            <iframe
                                srcDoc={previewHtml}
                                title="Email Preview"
                                className="w-full h-full border-0"
                                sandbox="allow-same-origin"
                            />
                        ) : (
                            <div className="flex items-center justify-center h-full text-muted-foreground">
                                Click Refresh to see preview
                            </div>
                        )}
                    </div>
                </div>

                {/* Test Email */}
                <div className="space-y-2 border-t pt-4">
                    <Label>Send Test Email</Label>
                    <div className="grid grid-cols-[1fr,2fr,auto] gap-2 items-end">
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
