import { useEffect, useState } from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface Props {
    name: string;
    onRename: (name: string) => void;
}

export function StepNameField({ name, onRename }: Props) {
    const [draft, setDraft] = useState(name);

    useEffect(() => {
        setDraft(name);
    }, [name]);

    const commit = () => {
        const trimmed = draft.trim();
        if (!trimmed) {
            setDraft(name);
            return;
        }
        if (trimmed !== name) {
            onRename(trimmed);
        }
    };

    return (
        <div className="space-y-1.5">
            <Label className="text-xs">Step name</Label>
            <Input
                className="h-8 text-sm font-mono"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onBlur={commit}
                onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                        e.currentTarget.blur();
                    }
                }}
                placeholder="unique_name"
                data-testid="properties-step-name"
            />
            <p className="text-[10px] text-muted-foreground">Must be unique; used as node id</p>
        </div>
    );
}
