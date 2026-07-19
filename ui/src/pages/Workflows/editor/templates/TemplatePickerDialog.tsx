/**
 * Template picker shown when creating a new workflow.
 * User must choose a template (including Empty) or Cancel back to the list.
 */

import { useRef } from 'react';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { GitMerge, LayoutTemplate } from 'lucide-react';
import { WORKFLOW_TEMPLATES, type WorkflowTemplate } from './workflowTemplates';
import { cn } from '@/lib/utils';

interface Props {
    open: boolean;
    onSelect: (template: WorkflowTemplate) => void;
    onCancel: () => void;
}

export function TemplatePickerDialog({ open, onSelect, onCancel }: Props) {
    // When parent closes after a successful select, Radix still fires onOpenChange(false).
    // Skip cancel navigation in that case.
    const selectingRef = useRef(false);

    const handleSelect = (tpl: WorkflowTemplate) => {
        selectingRef.current = true;
        onSelect(tpl);
    };

    return (
        <Dialog
            open={open}
            onOpenChange={(next) => {
                if (!next) {
                    if (selectingRef.current) {
                        selectingRef.current = false;
                        return;
                    }
                    onCancel();
                }
            }}
        >
            <DialogContent
                className="sm:max-w-2xl"
                data-testid="workflow-template-picker"
                // Require explicit Cancel (or Escape → onOpenChange) — no silent overlay dismiss
                onPointerDownOutside={(e) => e.preventDefault()}
                onInteractOutside={(e) => e.preventDefault()}
            >
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <LayoutTemplate className="h-5 w-5" />
                        Choose a template
                    </DialogTitle>
                    <DialogDescription>
                        Start from a pre-built automation or an empty canvas. You can rename and edit
                        everything after selecting.
                    </DialogDescription>
                </DialogHeader>

                <div className="grid gap-3 sm:grid-cols-2 py-2">
                    {WORKFLOW_TEMPLATES.map((tpl) => (
                        <button
                            key={tpl.id}
                            type="button"
                            data-testid={`workflow-template-${tpl.id}`}
                            onClick={() => handleSelect(tpl)}
                            className={cn(
                                'text-left rounded-lg border bg-card p-4 transition-colors',
                                'hover:border-primary hover:bg-muted/40 focus-visible:outline-none',
                                'focus-visible:ring-2 focus-visible:ring-ring',
                            )}
                        >
                            <div className="flex items-start justify-between gap-2 mb-1.5">
                                <span className="font-medium text-sm leading-tight">{tpl.name}</span>
                                <Badge variant="secondary" className="text-[10px] shrink-0">
                                    {tpl.nodeCount} node{tpl.nodeCount === 1 ? '' : 's'}
                                </Badge>
                            </div>
                            <p className="text-xs text-muted-foreground leading-relaxed">
                                {tpl.description}
                            </p>
                        </button>
                    ))}
                </div>

                <div className="flex justify-end gap-2 pt-1">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={onCancel}
                        data-testid="workflow-template-cancel"
                    >
                        Cancel
                    </Button>
                </div>

                <p className="text-[11px] text-muted-foreground flex items-center gap-1.5 -mt-1">
                    <GitMerge className="h-3 w-3" />
                    Templates seed the canvas only — nothing is saved until you click Save.
                </p>
            </DialogContent>
        </Dialog>
    );
}

export default TemplatePickerDialog;
