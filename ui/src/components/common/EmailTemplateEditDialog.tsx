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
import { Loader2, Send } from 'lucide-react';

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
            }),
        onSuccess: (data) => {
            toast({
                title: 'Test Email Sent',
                description: data.message,
            });
            setTestEmail('');
        },
        onError: (error: any) => {
            toast({
                title: 'Error',
                description: error.response?.data?.detail || 'Failed to send test email.',
                variant: 'destructive',
            });
        },
    });

    const handleSave = () => {
        updateMutation.mutate(formData);
    };

    const handleSendTest = () => {
        if (!testEmail) {
            toast({
                title: 'Error',
                description: 'Please enter a recipient email address.',
                variant: 'destructive',
            });
            return;
        }
        testEmailMutation.mutate(testEmail);
    };

    const insertVariable = (variable: string) => {
        const varText = `{{${variable}}}`;
        // Insert at cursor position in subject field (simple implementation)
        setFormData((prev) => ({
            ...prev,
            subject: (prev.subject || '') + varText,
        }));
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
                                    <SelectValue placeholder="Select a variable to insert" />
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
                            placeholder="Plain text email body"
                            className="font-mono text-sm min-h-[150px]"
                        />
                    </div>

                    {/* Test Email Section */}
                    <div className="space-y-2 pt-4 border-t">
                        <Label htmlFor="test_email">Send Test Email</Label>
                        <div className="flex gap-2">
                            <Input
                                id="test_email"
                                type="email"
                                value={testEmail}
                                onChange={(e) => setTestEmail(e.target.value)}
                                placeholder="recipient@example.com"
                            />
                            <Button
                                onClick={handleSendTest}
                                disabled={testEmailMutation.isPending}
                                variant="outline"
                            >
                                {testEmailMutation.isPending ? (
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                    <Send className="h-4 w-4" />
                                )}
                                <span className="ml-2">Send</span>
                            </Button>
                        </div>
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
        </Dialog>
    );
};
