import { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from '@/components/ui/dialog';
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
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

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

    const [focusedField, setFocusedField] = useState<'subject' | 'html_body' | 'text_body' | null>('subject');
    const [cursorPosition, setCursorPosition] = useState<number | null>(null);

    // ... (existing code)

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
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-3xl max-h-[90vh] flex flex-col">
                <DialogHeader>
                    <DialogTitle>
                        Edit Template: {template.template_type} ({template.locale})
                    </DialogTitle>
                </DialogHeader>

                <div className="flex-1 overflow-y-auto space-y-4 py-4">
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
                            className="font-mono text-sm min-h-[200px]"
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
                            className="font-mono text-sm min-h-[150px]"
                        />
                    </div>

                    {/* Test Email Section */}
                    <div className="space-y-4 pt-4 border-t">
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
                        {testResult && (
                            <Alert variant={testResult.success ? "default" : "destructive"} className="mt-4">
                                {testResult.success ? (
                                    <CheckCircle2 className="h-4 w-4" />
                                ) : (
                                    <XCircle className="h-4 w-4" />
                                )}
                                <AlertTitle>{testResult.success ? "Test Email Sent" : "Sending Failed"}</AlertTitle>
                                <AlertDescription>{testResult.message}</AlertDescription>
                            </Alert>
                        )}
                        <p className="text-xs text-muted-foreground">
                            Send a test email to verify the template renders correctly.
                        </p>
                    </div>

                    {/* Built-in Badge */}
                    {template.is_builtin && (
                        <div className="bg-secondary p-3 rounded-md">
                            <p className="text-sm text-muted-foreground">
                                This is a built-in template. Changes will be saved but you can reset to
                                default at any time.
                            </p>
                        </div>
                    )}
                </div>

                <DialogFooter>
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
                </DialogFooter>
            </DialogContent>
        </Dialog >
    );
};
