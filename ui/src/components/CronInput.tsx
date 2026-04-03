import { Lightbulb } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from '@/components/ui/popover';

const CRON_PRESETS = [
    { label: 'Every minute', value: '* * * * *' },
    { label: 'Every 5 minutes', value: '*/5 * * * *' },
    { label: 'Every 15 minutes', value: '*/15 * * * *' },
    { label: 'Every 30 minutes', value: '*/30 * * * *' },
    { label: 'Every hour', value: '0 * * * *' },
    { label: 'Daily at midnight', value: '0 0 * * *' },
    { label: 'Daily at 9am', value: '0 9 * * *' },
    { label: 'Weekdays at 9am', value: '0 9 * * 1-5' },
    { label: 'Every Monday at 9am', value: '0 9 * * 1' },
    { label: 'Monthly on the 1st', value: '0 0 1 * *' },
];

interface CronInputProps {
    id?: string;
    value: string;
    onChange: (value: string) => void;
    required?: boolean;
}

export function CronInput({ id = 'cron', value, onChange, required }: CronInputProps) {
    return (
        <div className="space-y-1.5">
            <div className="flex items-center justify-between">
                <Label htmlFor={id}>Cron Expression</Label>
                <Popover>
                    <PopoverTrigger asChild>
                        <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            className="h-7 gap-1 text-xs text-muted-foreground"
                        >
                            <Lightbulb className="h-3.5 w-3.5" />
                            Presets
                        </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-56 p-1" align="end">
                        <div className="space-y-0.5">
                            {CRON_PRESETS.map((preset) => (
                                <button
                                    key={preset.value}
                                    type="button"
                                    className="w-full rounded px-2 py-1.5 text-left text-sm hover:bg-muted"
                                    onClick={() => onChange(preset.value)}
                                >
                                    <span className="font-medium">{preset.label}</span>
                                    <span className="ml-2 font-mono text-xs text-muted-foreground">
                                        {preset.value}
                                    </span>
                                </button>
                            ))}
                        </div>
                    </PopoverContent>
                </Popover>
            </div>
            <Input
                id={id}
                placeholder="0 9 * * MON"
                className="font-mono"
                value={value}
                onChange={(e) => onChange(e.target.value)}
                required={required}
            />
            <p className="text-xs text-muted-foreground">
                Format: minute hour day month weekday (e.g.{' '}
                <code>0 9 * * 1-5</code> = weekdays at 9am)
            </p>
        </div>
    );
}
