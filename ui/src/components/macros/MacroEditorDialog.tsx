/**
 * Macro editor dialog component
 */

import { useState, useEffect } from 'react';
import { AppDialog } from '@/components/common/AppDialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { X, Plus, Info } from 'lucide-react';
import type { Macro, MacroCreate, MacroUpdate } from '@/types/macro';
import { handleApiError } from '@/lib/api';

interface MacroEditorDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSubmit: (data: MacroCreate | MacroUpdate) => Promise<void>;
    macro?: Macro | null;
}

export default function MacroEditorDialog({
    open,
    onOpenChange,
    onSubmit,
    macro,
}: MacroEditorDialogProps) {
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');
    const [sqlQuery, setSqlQuery] = useState('');
    const [parameters, setParameters] = useState<string[]>([]);
    const [newParameter, setNewParameter] = useState('');

    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (open) {
            if (macro) {
                setName(macro.name);
                setDescription(macro.description || '');
                setSqlQuery(macro.sql_query);
                try {
                    setParameters(JSON.parse(macro.parameters));
                } catch {
                    setParameters([]);
                }
            } else {
                setName('');
                setDescription('');
                setSqlQuery('');
                setParameters([]);
            }
            setError(null);
        }
    }, [open, macro]);

    const handleAddParameter = () => {
        if (newParameter && !parameters.includes(newParameter)) {
            setParameters([...parameters, newParameter]);
            setNewParameter('');
        }
    };

    const handleRemoveParameter = (index: number) => {
        setParameters(parameters.filter((_, i) => i !== index));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!name) {
            setError('Macro name is required');
            return;
        }

        if (!sqlQuery) {
            setError('SQL query is required');
            return;
        }

        setIsSubmitting(true);
        try {
            await onSubmit({
                name,
                description,
                sql_query: sqlQuery,
                parameters,
            });
            onOpenChange(false);
        } catch (err) {
            setError(handleApiError(err));
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <AppDialog
            open={open}
            onOpenChange={onOpenChange}
            title={macro ? 'Edit Macro' : 'Create Macro'}
            description="Define a reusable SQL snippet for permission rules. Use :param_name for parameters."
            className="max-w-2xl"
            footer={
                <>
                    <Button
                        type="button"
                        variant="outline"
                        onClick={() => onOpenChange(false)}
                        disabled={isSubmitting}
                    >
                        Cancel
                    </Button>
                    <Button type="submit" form="macro-editor-form" disabled={isSubmitting}>
                        {isSubmitting ? (macro ? 'Updating...' : 'Creating...') : (macro ? 'Update Macro' : 'Create Macro')}
                    </Button>
                </>
            }
        >
            <form id="macro-editor-form" onSubmit={handleSubmit} className="space-y-6">
                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <Label htmlFor="name">Macro Name</Label>
                        <div className="flex items-center gap-2">
                            <span className="text-muted-foreground">@</span>
                            <Input
                                id="name"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder="has_department_access"
                                disabled={isSubmitting}
                            />
                        </div>
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="description">Description (Optional)</Label>
                        <Input
                            id="description"
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            placeholder="Checks if user has access to a specific department"
                            disabled={isSubmitting}
                        />
                    </div>
                </div>

                <div className="space-y-2">
                    <Label htmlFor="sql">SQL Query</Label>
                    <Textarea
                        id="sql"
                        value={sqlQuery}
                        onChange={(e) => setSqlQuery(e.target.value)}
                        placeholder="SELECT 1 FROM departments WHERE id = :dept_id AND manager_id = :user_id"
                        className="font-mono min-h-[150px]"
                        disabled={isSubmitting}
                    />
                    <div className="flex items-center gap-2 text-xs text-muted-foreground bg-blue-50/50 p-2 rounded">
                        <Info className="h-3 w-3" />
                        <span>Available variables: record.*, user.*, :your_param</span>
                    </div>
                </div>

                <div className="space-y-3">
                    <Label>Parameters</Label>
                    <div className="flex flex-wrap gap-2 mb-2">
                        {parameters.map((param, index) => (
                            <Badge key={index} variant="secondary" className="gap-1 px-2 py-1">
                                {param}
                                {!isSubmitting && (
                                    <X
                                        className="h-3 w-3 cursor-pointer hover:text-destructive"
                                        onClick={() => handleRemoveParameter(index)}
                                    />
                                )}
                            </Badge>
                        ))}
                        {parameters.length === 0 && (
                            <span className="text-xs text-muted-foreground italic">No parameters defined</span>
                        )}
                    </div>
                    <div className="flex gap-2">
                        <Input
                            value={newParameter}
                            onChange={(e) => setNewParameter(e.target.value)}
                            placeholder="Parameter name (e.g. dept_id)"
                            onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                    e.preventDefault();
                                    handleAddParameter();
                                }
                            }}
                            disabled={isSubmitting}
                        />
                        <Button
                            type="button"
                            variant="outline"
                            size="icon"
                            onClick={handleAddParameter}
                            disabled={isSubmitting || !newParameter}
                        >
                            <Plus className="h-4 w-4" />
                        </Button>
                    </div>
                </div>

                {error && (
                    <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
                        <p className="text-destructive text-sm font-medium">{error}</p>
                    </div>
                )}
            </form>
        </AppDialog>
    );
}

// Internal Badge component if not imported correctly
function Badge({ children, variant = "default", className = "", ...props }: React.HTMLAttributes<HTMLDivElement> & { variant?: "default" | "secondary" | "destructive" | "outline" }) {
    const variants = {
        default: "bg-primary text-primary-foreground hover:bg-primary/80",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/80",
        outline: "text-foreground",
    };
    return (
        <div className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 ${variants[variant]} ${className}`} {...props}>
            {children}
        </div>
    );
}
