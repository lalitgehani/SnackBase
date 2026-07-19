/**
 * Keyboard-friendly outgoing edge controls for the properties panel.
 * Wires next / on_true / on_false without requiring canvas handle drag.
 */

import { Label } from '@/components/ui/label';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';

const NONE = '__none__';

interface SingleNextProps {
    id?: string;
    label?: string;
    value: string | null;
    options: string[];
    onChange: (targetId: string | null) => void;
    help?: string;
}

/** Single next-step select (action, wait, loop, trigger default out). */
export function NextStepSelect({
    id = 'prop-next-step',
    label = 'Next step',
    value,
    options,
    onChange,
    help = 'Connects this node to the next step (same as drawing an edge)',
}: SingleNextProps) {
    return (
        <div className="space-y-1.5">
            <Label htmlFor={id} className="text-xs">
                {label}
            </Label>
            <Select
                value={value ?? NONE}
                onValueChange={(v) => onChange(v === NONE ? null : v)}
            >
                <SelectTrigger id={id} className="h-8 text-sm" data-testid={id}>
                    <SelectValue placeholder="(end)" />
                </SelectTrigger>
                <SelectContent>
                    <SelectItem value={NONE} className="text-muted-foreground">
                        (end — no next)
                    </SelectItem>
                    {options.map((n) => (
                        <SelectItem key={n} value={n} className="font-mono">
                            {n}
                        </SelectItem>
                    ))}
                </SelectContent>
            </Select>
            {help && <p className="text-[10px] text-muted-foreground">{help}</p>}
        </div>
    );
}

interface ConditionBranchesProps {
    trueValue: string | null;
    falseValue: string | null;
    options: string[];
    onChangeTrue: (targetId: string | null) => void;
    onChangeFalse: (targetId: string | null) => void;
}

/** On true / on false selects for condition steps. */
export function ConditionBranchSelects({
    trueValue,
    falseValue,
    options,
    onChangeTrue,
    onChangeFalse,
}: ConditionBranchesProps) {
    return (
        <div className="space-y-3">
            <NextStepSelect
                id="prop-on-true"
                label="On true"
                value={trueValue}
                options={options}
                onChange={onChangeTrue}
                help="Wire the true branch without dragging on the canvas"
            />
            <NextStepSelect
                id="prop-on-false"
                label="On false"
                value={falseValue}
                options={options}
                onChange={onChangeFalse}
                help="Wire the false branch without dragging on the canvas"
            />
        </div>
    );
}
