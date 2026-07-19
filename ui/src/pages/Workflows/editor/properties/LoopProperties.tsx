import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import type { WorkflowStep } from '@/services/workflows.service';
import { StepNameField } from './StepNameField';

interface Props {
    step: WorkflowStep;
    otherStepNames: string[];
    onChange: (step: WorkflowStep) => void;
    onRename: (name: string) => void;
}

export function LoopProperties({ step, otherStepNames, onChange, onRename }: Props) {
    return (
        <div className="space-y-3" data-testid="properties-loop">
            <StepNameField name={step.name} onRename={onRename} />
            <div className="space-y-1.5">
                <Label className="text-xs">Items expression</Label>
                <Input
                    className="h-8 text-sm font-mono"
                    value={String(step.items ?? '')}
                    onChange={(e) => onChange({ ...step, items: e.target.value })}
                    placeholder="{{trigger.records}}"
                />
            </div>
            <div className="space-y-1.5">
                <Label className="text-xs">Body step</Label>
                <Select
                    value={String(step.step || '__none__')}
                    onValueChange={(v) =>
                        onChange({ ...step, step: v === '__none__' ? '' : v })
                    }
                >
                    <SelectTrigger className="h-8 text-sm">
                        <SelectValue placeholder="Select step…" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="__none__" className="text-muted-foreground">
                            (none)
                        </SelectItem>
                        {otherStepNames.map((n) => (
                            <SelectItem key={n} value={n} className="font-mono">
                                {n}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>
                <p className="text-[10px] text-muted-foreground">
                    Step to run for each item (engine reference)
                </p>
            </div>
        </div>
    );
}
