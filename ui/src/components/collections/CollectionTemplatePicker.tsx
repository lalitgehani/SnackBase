/**
 * Template strip for create collection (blank + starter schemas).
 */

import type { ComponentType } from 'react';
import { FileText, Package, Users, Square } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  BLANK_TEMPLATE_ID,
  COLLECTION_TEMPLATES,
  type CollectionTemplate,
} from '@/lib/collectionTemplates';

const ICONS: Record<string, ComponentType<{ className?: string }>> = {
  [BLANK_TEMPLATE_ID]: Square,
  posts: FileText,
  products: Package,
  contacts: Users,
};

export interface CollectionTemplatePickerProps {
  selectedId: string;
  onSelect: (templateId: string) => void;
  disabled?: boolean;
  /** Compact cards for empty-state grids */
  variant?: 'strip' | 'grid';
  className?: string;
}

const blankCard: Pick<
  CollectionTemplate,
  'id' | 'label' | 'description'
> = {
  id: BLANK_TEMPLATE_ID,
  label: 'Blank',
  description: 'Start with an empty schema',
};

export default function CollectionTemplatePicker({
  selectedId,
  onSelect,
  disabled = false,
  variant = 'strip',
  className,
}: CollectionTemplatePickerProps) {
  const items = [blankCard, ...COLLECTION_TEMPLATES];

  return (
    <div
      className={cn(
        variant === 'grid'
          ? 'grid gap-2 sm:grid-cols-2'
          : 'grid gap-2 sm:grid-cols-2 lg:grid-cols-4',
        className,
      )}
      data-testid="collection-template-picker"
      role="listbox"
      aria-label="Collection templates"
    >
      {items.map((item) => {
        const Icon = ICONS[item.id] ?? Square;
        const selected = selectedId === item.id;
        return (
          <button
            key={item.id}
            type="button"
            role="option"
            aria-selected={selected}
            disabled={disabled}
            data-testid={`template-${item.id}`}
            onClick={() => onSelect(item.id)}
            className={cn(
              'flex flex-col items-start gap-1 rounded-lg border p-3 text-left transition-colors',
              'hover:bg-accent/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              selected && 'border-primary bg-primary/5 ring-1 ring-primary',
              disabled && 'pointer-events-none opacity-50',
            )}
          >
            <div className="flex items-center gap-2">
              <Icon className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">{item.label}</span>
            </div>
            <span className="text-xs text-muted-foreground leading-snug">
              {item.description}
            </span>
          </button>
        );
      })}
    </div>
  );
}
