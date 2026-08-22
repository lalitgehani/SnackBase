import { Badge } from '@/components/ui/badge'
import type { EnvironmentStatus } from '@/types/control-plane'
import { cn } from '@/lib/utils'

/**
 * Environment lifecycle status → badge styling.
 *
 * | status       | intent        | color family   |
 * |--------------|---------------|----------------|
 * | pending      | queued        | muted gray     |
 * | provisioning | in progress   | blue           |
 * | ready        | success       | green          |
 * | failed       | error         | red            |
 * | deleting     | in progress   | amber          |
 * | deleted      | terminal      | muted outline  |
 */
export const ENVIRONMENT_STATUS_STYLES: Record<
  EnvironmentStatus,
  { label: string; className: string }
> = {
  pending: {
    label: 'Pending',
    className:
      'border-transparent bg-muted text-muted-foreground hover:bg-muted',
  },
  provisioning: {
    label: 'Provisioning',
    className:
      'border-transparent bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
  },
  ready: {
    label: 'Ready',
    className:
      'border-transparent bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
  },
  failed: {
    label: 'Failed',
    className:
      'border-transparent bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
  },
  deleting: {
    label: 'Deleting',
    className:
      'border-transparent bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-200',
  },
  deleted: {
    label: 'Deleted',
    className: 'border-border bg-background text-muted-foreground',
  },
}

export function getEnvironmentStatusMeta(status: string) {
  if (status in ENVIRONMENT_STATUS_STYLES) {
    return ENVIRONMENT_STATUS_STYLES[status as EnvironmentStatus]
  }
  return {
    label: status,
    className: 'border-transparent bg-muted text-muted-foreground',
  }
}

export interface EnvironmentStatusBadgeProps {
  status: string
  className?: string
}

export function EnvironmentStatusBadge({
  status,
  className,
}: EnvironmentStatusBadgeProps) {
  const meta = getEnvironmentStatusMeta(status)
  return (
    <Badge
      variant="outline"
      className={cn(meta.className, className)}
      data-testid="environment-status-badge"
      data-status={status}
    >
      {meta.label}
    </Badge>
  )
}
