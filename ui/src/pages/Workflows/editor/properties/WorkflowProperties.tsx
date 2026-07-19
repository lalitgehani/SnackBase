import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import type { EditorMetaFields } from './PropertiesPanel';

interface Props {
    meta: EditorMetaFields;
    onMetaChange: <K extends keyof EditorMetaFields>(key: K, value: EditorMetaFields[K]) => void;
    stepCount: number;
}

export function WorkflowProperties({ meta, onMetaChange, stepCount }: Props) {
    return (
        <div className="space-y-3" data-testid="properties-workflow">
            <p className="text-xs text-muted-foreground">
                Select a node to edit its configuration. Workflow metadata:
            </p>
            <div className="space-y-1.5">
                <Label htmlFor="prop-wf-name" className="text-xs">
                    Name
                </Label>
                <Input
                    id="prop-wf-name"
                    value={meta.name}
                    onChange={(e) => onMetaChange('name', e.target.value)}
                    className="h-8 text-sm"
                />
            </div>
            <div className="space-y-1.5">
                <Label htmlFor="prop-wf-desc" className="text-xs">
                    Description
                </Label>
                <Textarea
                    id="prop-wf-desc"
                    value={meta.description}
                    onChange={(e) => onMetaChange('description', e.target.value)}
                    className="text-sm min-h-[72px]"
                    placeholder="Optional description"
                />
            </div>
            <div className="flex items-center gap-2">
                <Switch
                    id="prop-wf-enabled"
                    checked={meta.enabled}
                    onCheckedChange={(v) => onMetaChange('enabled', v)}
                />
                <Label htmlFor="prop-wf-enabled" className="text-xs">
                    Enabled
                </Label>
            </div>
            <p className="text-xs text-muted-foreground pt-1">
                {stepCount} step{stepCount === 1 ? '' : 's'} on canvas
            </p>
        </div>
    );
}
