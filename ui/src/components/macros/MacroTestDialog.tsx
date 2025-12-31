/**
 * Macro test dialog component
 */

import { useState, useEffect } from 'react';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Play, CheckCircle2, AlertCircle, Clock, Hash } from 'lucide-react';
import type { Macro, MacroTestResponse } from '@/types/macro';
import { testMacro } from '@/services/macros.service';
import { handleApiError } from '@/lib/api';

interface MacroTestDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    macro: Macro | null;
}

export default function MacroTestDialog({
    open,
    onOpenChange,
    macro,
}: MacroTestDialogProps) {
    const [paramValues, setParamValues] = useState<any[]>([]);
    const [paramNames, setParamNames] = useState<string[]>([]);
    const [testResult, setTestResult] = useState<MacroTestResponse | null>(null);
    const [isTesting, setIsTesting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (open && macro) {
            try {
                const names = JSON.parse(macro.parameters);
                setParamNames(names);
                setParamValues(new Array(names.length).fill(''));
            } catch {
                setParamNames([]);
                setParamValues([]);
            }
            setTestResult(null);
            setError(null);
        }
    }, [open, macro]);

    const handleParamChange = (index: number, value: string) => {
        const newValues = [...paramValues];
        newValues[index] = value;
        setParamValues(newValues);
    };

    const handleTest = async () => {
        if (!macro) return;

        setIsTesting(true);
        setError(null);
        setTestResult(null);

        try {
            const result = await testMacro(macro.id, {
                parameters: paramValues,
            });
            setTestResult(result);
        } catch (err) {
            setError(handleApiError(err));
        } finally {
            setIsTesting(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Test Macro: @{macro?.name}</DialogTitle>
                    <DialogDescription>
                        Execute the macro in a transactional test mode. Changes will be rolled back.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-6 py-4">
                    {/* SQL Preview */}
                    <div className="space-y-2">
                        <Label className="text-xs uppercase text-muted-foreground font-semibold">SQL Query</Label>
                        <div className="bg-muted p-3 rounded-md font-mono text-sm overflow-x-auto whitespace-pre">
                            {macro?.sql_query}
                        </div>
                    </div>

                    {/* Parameters Input */}
                    <div className="space-y-4">
                        <Label className="text-xs uppercase text-muted-foreground font-semibold">Test Parameters</Label>
                        {paramNames.length === 0 ? (
                            <p className="text-sm text-muted-foreground italic">No parameters required for this macro.</p>
                        ) : (
                            <div className="grid gap-4">
                                {paramNames.map((name, index) => (
                                    <div key={index} className="space-y-2">
                                        <Label htmlFor={`param-${index}`} className="text-sm font-medium">
                                            {name}
                                        </Label>
                                        <Input
                                            id={`param-${index}`}
                                            value={paramValues[index]}
                                            onChange={(e) => handleParamChange(index, e.target.value)}
                                            placeholder={`Value for ${name}`}
                                            disabled={isTesting}
                                        />
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Actions */}
                    <Button
                        onClick={handleTest}
                        className="w-full gap-2"
                        disabled={isTesting || !macro}
                    >
                        {isTesting ? (
                            <Play className="h-4 w-4 animate-pulse" />
                        ) : (
                            <Play className="h-4 w-4" />
                        )}
                        {isTesting ? 'Executing...' : 'Run Test'}
                    </Button>

                    {/* Results */}
                    {testResult && (
                        <div className="space-y-4 p-4 border rounded-lg bg-green-50/30 border-green-100">
                            <div className="flex items-center gap-2 text-green-700 font-semibold">
                                <CheckCircle2 className="h-5 w-5" />
                                <span>Execution Successful</span>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-1">
                                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                                        <Hash className="h-3 w-3" />
                                        Result
                                    </div>
                                    <div className="font-mono text-sm break-all font-semibold">
                                        {testResult.result ?? 'null'}
                                    </div>
                                </div>
                                <div className="space-y-1">
                                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                                        <Clock className="h-3 w-3" />
                                        Execution Time
                                    </div>
                                    <div className="text-sm font-semibold">
                                        {testResult.execution_time.toFixed(2)} ms
                                    </div>
                                </div>
                            </div>

                            {testResult.rows_affected !== undefined && (
                                <div className="text-xs text-muted-foreground mt-2 italic px-1">
                                    Note: This was a read-only test. Any data modifications were rolled back.
                                </div>
                            )}
                        </div>
                    )}

                    {error && (
                        <div className="space-y-3 p-4 border rounded-lg bg-destructive/5 border-destructive/10">
                            <div className="flex items-center gap-2 text-destructive font-semibold">
                                <AlertCircle className="h-5 w-5" />
                                <span>Execution Failed</span>
                            </div>
                            <div className="text-sm text-muted-foreground whitespace-pre-wrap font-mono p-2 bg-destructive/5 rounded">
                                {error}
                            </div>
                        </div>
                    )}
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isTesting}>
                        Close
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
