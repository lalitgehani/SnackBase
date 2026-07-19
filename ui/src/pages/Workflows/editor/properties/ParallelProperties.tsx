import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Plus, X } from 'lucide-react';
import type { WorkflowStep } from '@/services/workflows.service';
import { StepNameField } from './StepNameField';

interface Props {
    step: WorkflowStep;
    otherStepNames: string[];
    onChange: (step: WorkflowStep) => void;
    onRename: (name: string) => void;
}

function asBranches(step: WorkflowStep): string[][] {
    const b = step.branches;
    if (!Array.isArray(b)) return [];
    return b.map((branch) =>
        Array.isArray(branch) ? branch.map((s) => String(s)) : [],
    );
}

export function ParallelProperties({ step, otherStepNames, onChange, onRename }: Props) {
    const branches = asBranches(step);

    const setBranches = (next: string[][]) => {
        onChange({ ...step, branches: next });
    };

    const addBranch = () => {
        setBranches([...branches, []]);
    };

    const removeBranch = (index: number) => {
        setBranches(branches.filter((_, i) => i !== index));
    };

    const setBranchStep = (branchIndex: number, stepName: string) => {
        const next = branches.map((b, i) => {
            if (i !== branchIndex) return b;
            if (!stepName) return [];
            // Single head step per branch for simplicity; can append later
            return [stepName];
        });
        setBranches(next);
    };

    const addStepToBranch = (branchIndex: number, stepName: string) => {
        if (!stepName) return;
        const next = branches.map((b, i) => (i === branchIndex ? [...b, stepName] : b));
        setBranches(next);
    };

    const removeStepFromBranch = (branchIndex: number, stepIndex: number) => {
        const next = branches.map((b, i) =>
            i === branchIndex ? b.filter((_, j) => j !== stepIndex) : b,
        );
        setBranches(next);
    };

    return (
        <div className="space-y-3" data-testid="properties-parallel">
            <StepNameField name={step.name} onRename={onRename} />
            <div className="space-y-2">
                <div className="flex items-center justify-between">
                    <Label className="text-xs">Branches</Label>
                    <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="h-7 text-xs"
                        onClick={addBranch}
                        data-testid="parallel-add-branch"
                    >
                        <Plus className="h-3 w-3 mr-1" />
                        Branch
                    </Button>
                </div>

                {branches.length === 0 && (
                    <p className="text-xs text-muted-foreground">No branches yet</p>
                )}

                {branches.map((branch, bi) => (
                    <div
                        key={bi}
                        className="border rounded-md p-2 space-y-2 bg-muted/30"
                        data-testid={`parallel-branch-${bi}`}
                    >
                        <div className="flex items-center justify-between">
                            <span className="text-xs font-medium">Branch {bi + 1}</span>
                            <Button
                                type="button"
                                variant="ghost"
                                size="icon"
                                className="h-6 w-6"
                                onClick={() => removeBranch(bi)}
                                aria-label={`Remove branch ${bi + 1}`}
                            >
                                <X className="h-3.5 w-3.5" />
                            </Button>
                        </div>

                        {branch.length > 0 ? (
                            <ul className="space-y-1">
                                {branch.map((sn, si) => (
                                    <li
                                        key={`${sn}-${si}`}
                                        className="flex items-center gap-1 text-xs font-mono bg-background rounded px-1.5 py-1"
                                    >
                                        <span className="flex-1 truncate">{sn}</span>
                                        <button
                                            type="button"
                                            className="text-muted-foreground hover:text-destructive"
                                            onClick={() => removeStepFromBranch(bi, si)}
                                            aria-label="Remove step from branch"
                                        >
                                            <X className="h-3 w-3" />
                                        </button>
                                    </li>
                                ))}
                            </ul>
                        ) : (
                            <p className="text-[10px] text-muted-foreground">Empty chain</p>
                        )}

                        <Select
                            value="__add__"
                            onValueChange={(v) => {
                                if (v !== '__add__') {
                                    if (branch.length === 0) setBranchStep(bi, v);
                                    else addStepToBranch(bi, v);
                                }
                            }}
                        >
                            <SelectTrigger className="h-7 text-xs">
                                <SelectValue placeholder="Add step…" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="__add__" disabled>
                                    Add step…
                                </SelectItem>
                                {otherStepNames.map((n) => (
                                    <SelectItem key={n} value={n} className="font-mono text-xs">
                                        {n}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                ))}
            </div>
        </div>
    );
}
