import type { LucideIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'

export interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description: string
  actionLabel?: string
  onAction?: () => void
  /** data-testid for the root container */
  testId?: string
  /** data-testid for the CTA button */
  actionTestId?: string
}

/**
 * Admin-style empty state: icon + title + description + optional primary CTA.
 */
export function EmptyState({
  icon: Icon,
  title,
  description,
  actionLabel,
  onAction,
  testId = 'empty-state',
  actionTestId = 'empty-state-cta',
}: EmptyStateProps) {
  return (
    <div className="py-12 text-center" data-testid={testId}>
      <Icon className="mx-auto mb-4 h-12 w-12 text-muted-foreground opacity-50" />
      <h3 className="mb-2 text-lg font-medium">{title}</h3>
      <p className="mx-auto mb-4 max-w-md text-muted-foreground">{description}</p>
      {actionLabel && onAction && (
        <Button onClick={onAction} data-testid={actionTestId}>
          {actionLabel}
        </Button>
      )}
    </div>
  )
}
