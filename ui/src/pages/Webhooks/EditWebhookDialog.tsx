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
import { webhooksService, type WebhookListItem } from '@/services/webhooks.service';
import { getCollections, type CollectionListItem } from '@/services/collections.service';
import { useToast } from '@/hooks/use-toast';
import { Plus, Trash2, Info, AlertTriangle } from 'lucide-react';

interface EditWebhookDialogProps {
    webhook: WebhookListItem | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onUpdated: () => void;
}

export function EditWebhookDialog({ webhook, open, onOpenChange, onUpdated }: EditWebhookDialogProps) {
    const [url, setUrl] = useState('');
    const [collection, setCollection] = useState('');
    const [events, setEvents] = useState<string[]>([]);
    const [filter, setFilter] = useState('');
    const [headers, setHeaders] = useState<{ key: string; value: string }[]>([]);
    const [collections, setCollections] = useState<CollectionListItem[]>([]);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const { toast } = useToast();

    useEffect(() => {
        if (open && webhook) {
            setUrl(webhook.url);
            setCollection(webhook.collection);
            setEvents(webhook.events);
            setFilter(webhook.filter || '');
            setHeaders(
                Object.entries(webhook.headers || {}).map(([key, value]) => ({ key, value }))
            );
            getCollections({ page_size: 100 }).then((r) => setCollections(r.items)).catch(() => {});
        }
    }, [open, webhook]);

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

    const handleUpdate = async () => {
        if (!webhook || !url || !collection || events.length === 0) return;

        const customHeaders = headers.reduce<Record<string, string>>((acc, { key, value }) => {
            if (key.trim()) acc[key.trim()] = value;
            return acc;
        }, {});

        setIsSubmitting(true);
        try {
            await webhooksService.update(webhook.id, {
                url,
                collection,
                events,
                filter: filter.trim() || null,
                headers: Object.keys(customHeaders).length > 0 ? customHeaders : null,
            });
            toast({ title: 'Webhook updated' });
            onUpdated();
            onOpenChange(false);
        } catch (error: any) {
            toast({
                title: 'Error updating webhook',
                description: error.response?.data?.detail || 'Something went wrong',
                variant: 'destructive',
            });
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <AppDialog
            open={open}
            onOpenChange={onOpenChange}
            title="Edit Webhook"
            description="Update the webhook configuration."
            className="sm:max-w-xl"
            footer={
                <>
                    <Button variant="ghost" onClick={() => onOpenChange(false)}>
                        Cancel
                    </Button>
                    <Button
                        onClick={handleUpdate}
                        disabled={!url || !collection || events.length === 0 || isSubmitting}
                    >
                        {isSubmitting ? 'Saving...' : 'Save Changes'}
                    </Button>
                </>
            }
        >
            <div className="space-y-4">
                <Alert className="bg-blue-50 border-blue-200 text-blue-900">
                    <Info className="h-4 w-4 text-blue-600" />
                    <AlertDescription>
                        The signing secret cannot be viewed again. Use "Regenerate Secret" if you need a new one (not yet implemented — contact support).
                    </AlertDescription>
                </Alert>

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
                                    id={`edit-event-${event}`}
                                    checked={events.includes(event)}
                                    onCheckedChange={() => toggleEvent(event)}
                                />
                                <Label htmlFor={`edit-event-${event}`} className="capitalize cursor-pointer">
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
                            placeholder='e.g. status = "published"'
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
            </div>
        </AppDialog>
    );
}
