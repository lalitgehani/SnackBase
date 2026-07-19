import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import type { WorkflowStep } from '@/services/workflows.service';
import { StepNameField } from './StepNameField';

interface Props {
    step: WorkflowStep;
    onChange: (step: WorkflowStep) => void;
    onRename: (name: string) => void;
}

export function ConditionProperties({ step, onChange, onRename }: Props) {
    return (
        <div className="space-y-3" data-testid="properties-condition">
            <StepNameField name={step.name} onRename={onRename} />
            <div className="space-y-1.5">
                <Label className="text-xs">Expression</Label>
                <Input
                    className="h-8 text-sm font-mono"
                    value={String(step.expression ?? '')}
                    onChange={(e) => onChange({ ...step, expression: e.target.value })}
                    placeholder='status == "approved"'
                />
                <p className="text-[10px] text-muted-foreground">
                    Wire true / false branches by connecting handles on the canvas
                </p>
            </div>
        </div>
    );
}
