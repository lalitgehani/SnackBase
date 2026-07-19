/**
 * Left-rail palette: searchable step types with drag + click-to-add.
 */

import { useMemo, useState } from 'react';
import {
    GitBranch,
    GitFork,
    Hourglass,
    Play,
    Radio,
    Repeat,
    Timer,
    type LucideIcon,
} from 'lucide-react';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import {
    PALETTE_DND_TYPE,
    PALETTE_GROUPS,
    type StepTypeValue,
} from '../../workflowConstants';

const ICONS: Record<StepTypeValue, LucideIcon> = {
    action: Play,
    condition: GitBranch,
    wait_delay: Timer,
    wait_condition: Hourglass,
    wait_event: Radio,
    loop: Repeat,
    parallel: GitFork,
};

export interface NodePaletteProps {
    onAddStep: (stepType: StepTypeValue) => void;
    readOnly?: boolean;
    className?: string;
}

export function NodePalette({ onAddStep, readOnly = false, className }: NodePaletteProps) {
    const [query, setQuery] = useState('');

    const groups = useMemo(() => {
        const q = query.trim().toLowerCase();
        if (!q) return PALETTE_GROUPS;
        return PALETTE_GROUPS.map((g) => ({
            ...g,
            items: g.items.filter(
                (item) =>
                    item.label.toLowerCase().includes(q) ||
                    item.description.toLowerCase().includes(q) ||
                    item.stepType.toLowerCase().includes(q),
            ),
        })).filter((g) => g.items.length > 0);
    }, [query]);

    const onDragStart = (event: React.DragEvent, stepType: StepTypeValue) => {
        if (readOnly) {
            event.preventDefault();
            return;
        }
        event.dataTransfer.setData(PALETTE_DND_TYPE, stepType);
        event.dataTransfer.effectAllowed = 'move';
    };

    return (
        <aside
            className={cn('flex flex-col h-full min-h-0', className)}
            data-testid="workflow-editor-palette"
        >
            <div className="p-3 border-b shrink-0 space-y-2">
                <p className="text-sm font-medium">Steps</p>
                <Input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Search…"
                    className="h-8 text-sm"
                    disabled={readOnly}
                    data-testid="workflow-palette-search"
                />
            </div>

            <div className="flex-1 overflow-y-auto p-2 space-y-3">
                {groups.length === 0 && (
                    <p className="text-xs text-muted-foreground px-1 py-2">No matching steps</p>
                )}
                {groups.map((group) => (
                    <div key={group.id}>
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground px-1 mb-1">
                            {group.label}
                        </p>
                        <ul className="space-y-1">
                            {group.items.map((item) => {
                                const Icon = ICONS[item.stepType];
                                return (
                                    <li key={item.stepType}>
                                        <button
                                            type="button"
                                            draggable={!readOnly}
                                            onDragStart={(e) => onDragStart(e, item.stepType)}
                                            onClick={() => {
                                                if (!readOnly) onAddStep(item.stepType);
                                            }}
                                            disabled={readOnly}
                                            className={cn(
                                                'w-full flex items-start gap-2 rounded-md border bg-card px-2 py-2 text-left transition-colors',
                                                'hover:bg-accent/50 hover:border-accent-foreground/20',
                                                'disabled:opacity-50 disabled:pointer-events-none',
                                                'cursor-grab active:cursor-grabbing',
                                            )}
                                            data-testid={`palette-item-${item.stepType}`}
                                        >
                                            <Icon className="h-4 w-4 shrink-0 mt-0.5 text-muted-foreground" />
                                            <span className="min-w-0">
                                                <span className="block text-xs font-medium leading-tight">
                                                    {item.label}
                                                </span>
                                                <span className="block text-[10px] text-muted-foreground leading-snug mt-0.5">
                                                    {item.description}
                                                </span>
                                            </span>
                                        </button>
                                    </li>
                                );
                            })}
                        </ul>
                    </div>
                ))}
            </div>

            <p className="text-[10px] text-muted-foreground px-3 py-2 border-t shrink-0">
                Drag onto canvas or click to add
            </p>
        </aside>
    );
}

export default NodePalette;
