import { useState } from 'react';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import type { WorkflowStep } from '@/services/workflows.service';
import { ACTION_TYPES } from '../../workflowConstants';
import { parseActionConfigJson } from '../nodeDefaults';
import { StepNameField } from './StepNameField';

interface Props {
    step: WorkflowStep;
    onChange: (step: WorkflowStep) => void;
    onRename: (name: string) => void;
}

/** Parent should set `key={nodeId}` so JSON draft resets on selection change. */
export function ActionProperties({ step, onChange, onRename }: Props) {
    const [configText, setConfigText] = useState(() =>
        JSON.stringify((step.config as object) ?? {}, null, 2),
    );
    const [jsonError, setJsonError] = useState<string | null>(null);

    const applyConfig = (raw: string) => {
        setConfigText(raw);
        const result = parseActionConfigJson(raw);
        if (!result.ok) {
            setJsonError(result.error);
            return;
        }
        setJsonError(null);
        onChange({ ...step, config: result.value });
    };

    return (
        <div className="space-y-3" data-testid="properties-action">
            <StepNameField name={step.name} onRename={onRename} />
            <div className="space-y-1.5">
                <Label htmlFor="prop-action-type" className="text-xs">
                    Action type
                </Label>
                <Select
                    value={String(step.action_type ?? 'send_webhook')}
                    onValueChange={(v) => onChange({ ...step, action_type: v })}
                >
                    <SelectTrigger id="prop-action-type" className="h-8 text-sm">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        {ACTION_TYPES.map((a) => (
                            <SelectItem key={a.value} value={a.value}>
                                {a.label}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>
            </div>
            <div className="space-y-1.5">
                <Label htmlFor="prop-action-config" className="text-xs">
                    Config (JSON)
                </Label>
                <Textarea
                    id="prop-action-config"
                    className="text-xs font-mono min-h-[120px]"
                    value={configText}
                    onChange={(e) => applyConfig(e.target.value)}
                    data-testid="properties-action-config"
                />
                {jsonError && (
                    <p className="text-xs text-destructive" data-testid="properties-action-json-error">
                        {jsonError}
                    </p>
                )}
            </div>
        </div>
    );
}
