import { Button } from '@/components/ui/button';
import { ChevronDown, ChevronUp, Plus, Trash2 } from 'lucide-react';
import type { HookAction } from '@/services/hooks.service';
import { actionAccentClass, actionSummary } from '../HookStatusBadge';
import { ACTION_TYPES } from '../hookConstants';
import { cn } from '@/lib/utils';

interface Props {
  actions: HookAction[];
  selectedIndex: number | null;
  onSelect: (index: number) => void;
  onAdd: () => void;
  onMove: (index: number, direction: -1 | 1) => void;
  onRemove: (index: number) => void;
}

function actionLabel(type: string): string {
  return ACTION_TYPES.find((a) => a.value === type)?.label ?? type;
}

export function ActionPipeline({
  actions,
  selectedIndex,
  onSelect,
  onAdd,
  onMove,
  onRemove,
}: Props) {
  return (
    <div className="flex flex-col h-full min-h-0" data-testid="action-pipeline">
      <div className="shrink-0 flex items-center justify-between px-3 py-2 border-b">
        <p className="text-sm font-medium">Actions</p>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="h-7 text-xs"
          onClick={onAdd}
          data-testid="add-action"
        >
          <Plus className="h-3.5 w-3.5 mr-1" />
          Add action
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {actions.length === 0 ? (
          <div
            className="text-center py-10 px-4 border border-dashed rounded-lg space-y-3"
            data-testid="action-pipeline-empty"
          >
            <p className="text-sm text-muted-foreground">
              No actions yet. Add at least one action to execute when the hook fires.
            </p>
            <Button type="button" size="sm" onClick={onAdd} data-testid="add-action-empty">
              <Plus className="h-3.5 w-3.5 mr-1" />
              Add first action
            </Button>
            <p className="text-xs text-muted-foreground">
              Variables:{' '}
              <code className="bg-muted px-1 rounded">{'{{record.field}}'}</code>{' '}
              <code className="bg-muted px-1 rounded">{'{{auth.user_id}}'}</code>{' '}
              <code className="bg-muted px-1 rounded">{'{{auth.email}}'}</code>{' '}
              <code className="bg-muted px-1 rounded">{'{{now}}'}</code>
            </p>
          </div>
        ) : (
          actions.map((action, index) => {
            const selected = selectedIndex === index;
            return (
              <div
                key={index}
                role="button"
                tabIndex={0}
                data-testid={`action-item-${index}`}
                onClick={() => onSelect(index)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onSelect(index);
                  }
                }}
                className={cn(
                  'border border-l-4 rounded-md p-3 bg-card cursor-pointer transition-shadow',
                  actionAccentClass(action.type),
                  selected && 'ring-2 ring-ring shadow-sm',
                )}
              >
                <div className="flex items-start gap-2">
                  <span className="text-xs font-mono text-muted-foreground w-5 shrink-0 pt-0.5">
                    {index + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{actionLabel(action.type)}</p>
                    <p className="text-xs text-muted-foreground truncate mt-0.5">
                      {actionSummary(action)}
                    </p>
                  </div>
                  <div className="flex items-center gap-0.5 shrink-0" onClick={(e) => e.stopPropagation()}>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      disabled={index === 0}
                      onClick={() => onMove(index, -1)}
                      data-testid={`action-move-up-${index}`}
                    >
                      <ChevronUp className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      disabled={index === actions.length - 1}
                      onClick={() => onMove(index, 1)}
                      data-testid={`action-move-down-${index}`}
                    >
                      <ChevronDown className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-destructive"
                      onClick={() => onRemove(index)}
                      data-testid={`action-remove-${index}`}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
