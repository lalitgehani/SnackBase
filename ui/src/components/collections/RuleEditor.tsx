import React from 'react';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Lock, Unlock, Code, HelpCircle } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

interface RuleEditorProps {
    label: string;
    description: string;
    value: string | null;
    onChange: (value: string | null) => void;
    onTest?: () => void;
    placeholder?: string;
}

export default function RuleEditor({
    label,
    description,
    value,
    onChange,
    onTest,
    placeholder = 'e.g. created_by = @request.auth.id',
}: RuleEditorProps) {
    const isLocked = value === null;
    const isPublic = value === '';
    const isCustom = value !== null && value !== '';

    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between">
                <div>
                    <Label className="text-base font-semibold">{label}</Label>
                    <p className="text-sm text-muted-foreground">{description}</p>
                </div>
                {isCustom && onTest && (
                    <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={onTest}
                        className="h-8 gap-1"
                    >
                        <Code className="h-3.5 w-3.5" />
                        Test Rule
                    </Button>
                )}
            </div>

            <div className="flex flex-col gap-3 p-4 border rounded-lg bg-card text-card-foreground shadow-sm">
                <div className="flex items-center gap-2">
                    <Button
                        type="button"
                        variant={isLocked ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => onChange(null)}
                        className={cn("flex-1 gap-2", isLocked && "bg-red-600 hover:bg-red-700 text-white")}
                    >
                        <Lock className="h-4 w-4" />
                        Locked
                    </Button>
                    <Button
                        type="button"
                        variant={isPublic ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => onChange('')}
                        className={cn("flex-1 gap-2", isPublic && "bg-green-600 hover:bg-green-700 text-white")}
                    >
                        <Unlock className="h-4 w-4" />
                        Public
                    </Button>
                    <Button
                        type="button"
                        variant={isCustom ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => {
                            if (!isCustom) onChange('created_by = @request.auth.id');
                        }}
                        className="flex-1 gap-2"
                    >
                        <Code className="h-4 w-4" />
                        Custom
                    </Button>
                </div>

                {isCustom && (
                    <div className="mt-2 space-y-2">
                        <div className="relative">
                            <Input
                                value={value}
                                onChange={(e) => onChange(e.target.value)}
                                placeholder={placeholder}
                                className="font-mono text-sm pr-10"
                            />
                            <TooltipProvider>
                                <Tooltip>
                                    <TooltipTrigger asChild>
                                        <div className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground cursor-help">
                                            <HelpCircle className="h-4 w-4" />
                                        </div>
                                    </TooltipTrigger>
                                    <TooltipContent side="left" className="max-w-[300px]">
                                        <p className="text-xs">
                                            Supported variables:<br />
                                            - <code className="text-primary">@request.auth.id</code><br />
                                            - <code className="text-primary">@request.auth.role</code><br />
                                            - <code className="text-primary">created_by</code>, <code className="text-primary">id</code>, etc.<br />
                                            <br />
                                            Operators: <code className="text-primary">=</code>, <code className="text-primary">!=</code>, <code className="text-primary">&amp;&amp;</code>, <code className="text-primary">||</code>
                                        </p>
                                    </TooltipContent>
                                </Tooltip>
                            </TooltipProvider>
                        </div>
                    </div>
                )}

                {isLocked && (
                    <p className="text-xs text-muted-foreground text-center mt-1">
                        Only superadmins can access this operation.
                    </p>
                )}
                {isPublic && (
                    <p className="text-xs text-muted-foreground text-center mt-1">
                        Anyone (including unauthenticated users) can access this operation.
                    </p>
                )}
            </div>
        </div>
    );
}
