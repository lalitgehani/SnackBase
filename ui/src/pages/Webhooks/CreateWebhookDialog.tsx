import { useEffect, useState } from 'react';
import { AppDialog } from '@/components/common/AppDialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Field, FieldLabel, FieldContent } from '@/components/ui/field';
import { webhooksService, type WebhookCreateResponse } from '@/services/webhooks.service';
import { getCollections, type CollectionListItem } from '@/services/collections.service';
import { useToast } from '@/hooks/use-toast';
import { Copy, Info, AlertTriangle, Plus, Trash2 } from 'lucide-react';

interface CreateWebhookDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onCreated: () => void;
}

function generateSecret(): string {
    const array = new Uint8Array(24);
    crypto.getRandomValues(array);
    return Array.from(array, (b) => b.toString(16).padStart(2, '0')).join('');
}

export function CreateWebhookDialog({ open, onOpenChange, onCreated }: CreateWebhookDialogProps) {
    const [url, setUrl] = useState('');
    const [collection, setCollection] = useState('');
    const [events, setEvents] = useState<string[]>(['create']);
    const [filter, setFilter] = useState('');
    const [secret, setSecret] = useState(() => generateSecret());
    const [headers, setHeaders] = useState<{ key: string; value: string }[]>([]);
    const [collections, setCollections] = useState<CollectionListItem[]>([]);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [createdWebhook, setCreatedWebhook] = useState<WebhookCreateResponse | null>(null);
    const [secretCopied, setSecretCopied] = useState(false);
    const { toast } = useToast();

    useEffect(() => {
        if (open) {
            getCollections({ page_size: 100 }).then((r) => setCollections(r.items)).catch(() => {});
        }
    }, [open]);

    const toggleEvent = (event: string) => {
        setEvents((prev) =>
            prev.includes(event) ? prev.filter((e) => e !== event) : [...prev, event]
        );
    };

    const addHeader = () => setHeaders((prev) => [...prev, { key: '', value: '' }]);
    const removeHeader = (i: number) => setHeaders((prev) => prev.filter((_, idx) => idx !== i));
    const updateHeader = (i: number, field: 'key' | 'value', val: string) => {
        setHeaders((prev) => prev.map((h, idx) => (idx === i ? { ...h, [field]: val } : h)));
    };

    const handleCreate = async () => {
        if (!url || !collection || events.length === 0) return;

        const customHeaders = headers.reduce<Record<string, string>>((acc, { key, value }) => {
            if (key.trim()) acc[key.trim()] = value;
            return acc;
        }, {});

        setIsSubmitting(true);
        try {
            const result = await webhooksService.create({
                url,
                collection,
                events,
                secret,
                filter: filter.trim() || null,
                headers: Object.keys(customHeaders).length > 0 ? customHeaders : null,
            });
            setCreatedWebhook(result);
            onCreated();
        } catch (error: any) {
            toast({
                title: 'Error creating webhook',
                description: error.response?.data?.detail || 'Something went wrong',
                variant: 'destructive',
            });
        } finally {
            setIsSubmitting(false);
        }
    };

    const copySecret = async () => {
        await navigator.clipboard.writeText(createdWebhook?.secret || secret);
        setSecretCopied(true);
        setTimeout(() => setSecretCopied(false), 2000);
    };

    const resetAndClose = () => {
        setUrl('');
        setCollection('');
        setEvents(['create']);
        setFilter('');
        setSecret(generateSecret());
        setHeaders([]);
        setCreatedWebhook(null);
        setSecretCopied(false);
        onOpenChange(false);
    };

    if (createdWebhook) {
        return (
            <AppDialog
                open={open}
                onOpenChange={resetAndClose}
                title="Webhook Created"
                description="Save your signing secret now — it will never be shown again."
                className="sm:max-w-lg"
                footer={<Button onClick={resetAndClose}>Done</Button>}
            >
                <div className="space-y-4">
                    <Alert className="bg-amber-50 border-amber-200 text-amber-900">
                        <AlertTriangle className="h-4 w-4 text-amber-600" />
                        <AlertDescription>
                            This secret is used to verify webhook signatures (X-SnackBase-Signature header).
                            Store it securely — it cannot be retrieved later.
                        </AlertDescription>
                    </Alert>
                    <div>
                        <p className="text-sm font-medium mb-1">Signing Secret</p>
                        <div className="flex items-center gap-2 bg-muted px-3 py-2 rounded border font-mono text-sm break-all">
                            <span className="flex-1 select-all">{createdWebhook.secret}</span>
                            <Button variant="ghost" size="sm" onClick={copySecret} className="shrink-0">
                                <Copy className="h-4 w-4" />
                                {secretCopied ? 'Copied!' : 'Copy'}
                            </Button>
                        </div>
                    </div>
                </div>
            </AppDialog>
        );
    }

    return (
        <AppDialog
            open={open}
            onOpenChange={onOpenChange}
            title="Create Webhook"
            description="Configure an outbound webhook to notify external services on record changes."
            className="sm:max-w-xl"
            footer={
                <>
                    <Button variant="ghost" onClick={() => onOpenChange(false)}>
                        Cancel
                    </Button>
                    <Button
                        onClick={handleCreate}
                        disabled={!url || !collection || events.length === 0 || isSubmitting}
                    >
                        {isSubmitting ? 'Creating...' : 'Create Webhook'}
                    </Button>
                </>
            }
        >
            <div className="space-y-4">
                <Field>
                    <FieldLabel>URL <span className="text-destructive">*</span></FieldLabel>
                    <FieldContent>
                        <Input
                            placeholder="https://example.com/webhook"
                            value={url}
                            onChange={(e) => setUrl(e.target.value)}
                        />
                        <p className="text-xs text-muted-foreground">HTTPS required in production.</p>
                    </FieldContent>
                </Field>

                <Field>
                    <FieldLabel>Collection <span className="text-destructive">*</span></FieldLabel>
                    <FieldContent>
                        <Select value={collection} onValueChange={setCollection}>
                            <SelectTrigger>
                                <SelectValue placeholder="Select a collection" />
                            </SelectTrigger>
                            <SelectContent>
                                {collections.map((c) => (
                                    <SelectItem key={c.id} value={c.name}>
                                        {c.name}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </FieldContent>
                </Field>

                <div>
                    <p className="text-sm font-medium mb-2">Events <span className="text-destructive">*</span></p>
                    <div className="flex gap-4">
                        {['create', 'update', 'delete'].map((event) => (
                            <div key={event} className="flex items-center gap-2">
                                <Checkbox
                                    id={`event-${event}`}
                                    checked={events.includes(event)}
                                    onCheckedChange={() => toggleEvent(event)}
                                />
                                <Label htmlFor={`event-${event}`} className="capitalize cursor-pointer">
                                    {event}
                                </Label>
                            </div>
                        ))}
                    </div>
                </div>

                <Field>
                    <FieldLabel>Filter (optional)</FieldLabel>
                    <FieldContent>
                        <Textarea
                            placeholder='e.g. status = "published" and @has_role("admin")'
                            value={filter}
                            onChange={(e) => setFilter(e.target.value)}
                            rows={2}
                        />
                        <p className="text-xs text-muted-foreground">
                            Rule expression — webhook only fires if the record matches.
                        </p>
                    </FieldContent>
                </Field>

                <div>
                    <div className="flex items-center justify-between mb-2">
                        <p className="text-sm font-medium">Custom Headers (optional)</p>
                        <Button variant="outline" size="sm" onClick={addHeader}>
                            <Plus className="h-3 w-3 mr-1" /> Add Header
                        </Button>
                    </div>
                    {headers.length > 0 && (
                        <div className="space-y-2">
                            {headers.map((h, i) => (
                                <div key={i} className="flex gap-2 items-center">
                                    <Input
                                        placeholder="Header name"
                                        value={h.key}
                                        onChange={(e) => updateHeader(i, 'key', e.target.value)}
                                        className="flex-1"
                                    />
                                    <Input
                                        placeholder="Value"
                                        value={h.value}
                                        onChange={(e) => updateHeader(i, 'value', e.target.value)}
                                        className="flex-1"
                                    />
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => removeHeader(i)}
                                        className="text-muted-foreground hover:text-destructive"
                                    >
                                        <Trash2 className="h-4 w-4" />
                                    </Button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                <div>
                    <p className="text-sm font-medium mb-1">Signing Secret</p>
                    <div className="flex items-center gap-2">
                        <Input value={secret} readOnly className="font-mono text-xs" />
                        <Button variant="outline" size="sm" onClick={copySecret} className="shrink-0">
                            <Copy className="h-4 w-4" />
                        </Button>
                    </div>
                    <div className="flex items-start gap-1 mt-1">
                        <Info className="h-3 w-3 text-muted-foreground mt-0.5 shrink-0" />
                        <p className="text-xs text-muted-foreground">
                            Auto-generated. Used to verify webhook signatures via the X-SnackBase-Signature header. Shown once only.
                        </p>
                    </div>
                </div>
            </div>
        </AppDialog>
    );
}
