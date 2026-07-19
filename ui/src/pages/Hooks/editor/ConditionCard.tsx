import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import type { HookFormState } from './hookFormState';

interface Props {
  form: HookFormState;
  onChange: (patch: Partial<HookFormState>) => void;
}

export function ConditionCard({ form, onChange }: Props) {
  return (
    <div className="rounded-lg border bg-card p-3 space-y-2" data-testid="condition-card">
      <Label htmlFor="hook-condition">
        Condition <span className="font-normal text-muted-foreground">(optional)</span>
      </Label>
      <Input
        id="hook-condition"
        placeholder='status = "active" AND role != "admin"'
        value={form.condition}
        onChange={(e) => onChange({ condition: e.target.value })}
        data-testid="condition-input"
      />
      <p className="text-xs text-muted-foreground">
        Rule expression must be true for actions to run.
      </p>
    </div>
  );
}
