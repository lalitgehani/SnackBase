/**
 * Template picker shown when creating a new hook.
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
import { LayoutTemplate } from 'lucide-react';
import { HOOK_TEMPLATES, type HookTemplate } from './hookTemplates';
import { cn } from '@/lib/utils';

interface Props {
  open: boolean;
  onSelect: (template: HookTemplate) => void;
  onCancel: () => void;
}

export function TemplatePickerDialog({ open, onSelect, onCancel }: Props) {
  const selectingRef = useRef(false);

  const handleSelect = (tpl: HookTemplate) => {
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
        data-testid="hook-template-picker"
        onPointerDownOutside={(e) => e.preventDefault()}
        onInteractOutside={(e) => e.preventDefault()}
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <LayoutTemplate className="h-5 w-5" />
            Choose a template
          </DialogTitle>
          <DialogDescription>
            Start from a pre-built automation or an empty hook. You can rename and edit
            everything after selecting.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-3 sm:grid-cols-2 py-2">
          {HOOK_TEMPLATES.map((tpl) => (
            <button
              key={tpl.id}
              type="button"
              data-testid={`hook-template-${tpl.id}`}
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
                  {tpl.actionCount} action{tpl.actionCount === 1 ? '' : 's'}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">{tpl.description}</p>
            </button>
          ))}
        </div>

        <div className="flex justify-end gap-2 pt-1">
          <Button
            variant="outline"
            size="sm"
            onClick={onCancel}
            data-testid="hook-template-cancel"
          >
            Cancel
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
