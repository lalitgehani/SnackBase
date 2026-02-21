/**
 * Macro detail dialog component (Read-only)
 */

import { AppDialog } from '@/components/common/AppDialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Calendar, User, Code2, Info, Terminal } from 'lucide-react';
import type { Macro } from '@/types/macro';
import { format } from 'date-fns';

interface MacroDetailDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    macro: Macro | null;
    onTest: (macro: Macro) => void;
    onEdit: (macro: Macro) => void;
}

export default function MacroDetailDialog({
    open,
    onOpenChange,
    macro,
    onTest,
    onEdit,
}: MacroDetailDialogProps) {
    if (!macro) return null;

    let params: string[] = [];
    try {
        params = JSON.parse(macro.parameters);
    } catch {
        params = [];
    }

    return (
        <AppDialog
            open={open}
            onOpenChange={onOpenChange}
            title={
                <span className="text-2xl flex items-center gap-2">
                    <span className="text-primary">@</span>
                    {macro.name}
                </span>
            }
            description={macro.description || 'No description provided.'}
            className="max-w-2xl"
            footer={
                <div className="flex gap-2 w-full sm:w-auto justify-between w-full">
                    <div className="flex gap-2">
                        <Button
                            variant="secondary"
                            className="flex-1 sm:flex-none gap-2"
                            onClick={() => {
                                onOpenChange(false);
                                onTest(macro);
                            }}
                        >
                            <Terminal className="h-4 w-4" />
                            Test Macro
                        </Button>
                        <Button
                            variant="outline"
                            className="flex-1 sm:flex-none"
                            onClick={() => {
                                onOpenChange(false);
                                onEdit(macro);
                            }}
                        >
                            Edit
                        </Button>
                    </div>
                    <Button variant="ghost" onClick={() => onOpenChange(false)}>
                        Close
                    </Button>
                </div>
            }
        >
            <div className="space-y-6">
                <div className="flex items-center gap-2 mb-1">
                    <Badge variant="outline" className="text-primary border-primary/20 bg-primary/5">
                        Macro
                    </Badge>
                    <span className="text-sm text-muted-foreground font-mono">ID: {macro.id}</span>
                </div>

                {/* Metadata Grid */}
                <div className="grid grid-cols-2 gap-4">
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Calendar className="h-4 w-4" />
                        <span>Updated: {format(new Date(macro.updated_at), 'PPP pp')}</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <User className="h-4 w-4" />
                        <span>Created by: {macro.created_by || 'System'}</span>
                    </div>
                </div>

                {/* Parameters Section */}
                <div className="space-y-3">
                    <Label className="text-xs uppercase text-muted-foreground font-semibold flex items-center gap-1.5">
                        <Info className="h-3.5 w-3.5" />
                        Parameters ({params.length})
                    </Label>
                    <div className="flex flex-wrap gap-2">
                        {params.map((param, index) => (
                            <Badge key={index} variant="secondary">
                                {param}
                            </Badge>
                        ))}
                        {params.length === 0 && (
                            <span className="text-sm text-muted-foreground italic">No parameters</span>
                        )}
                    </div>
                </div>

                {/* SQL Section */}
                <div className="space-y-3">
                    <Label className="text-xs uppercase text-muted-foreground font-semibold flex items-center gap-1.5">
                        <Code2 className="h-3.5 w-3.5" />
                        SQL Implementation
                    </Label>
                    <div className="bg-slate-950 text-slate-50 p-4 rounded-lg font-mono text-sm overflow-x-auto whitespace-pre leading-relaxed shadow-inner">
                        {macro.sql_query}
                    </div>
                </div>
            </div>
        </AppDialog>
    );
}
