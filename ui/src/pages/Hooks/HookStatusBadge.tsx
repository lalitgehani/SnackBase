/**
 * Shared presentation helpers for Hooks list + overview.
 */

import type { Hook, HookAction, HookExecution } from '@/services/hooks.service';

export function formatHookDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleString();
}

export function formatDurationMs(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return '—';
  return `${ms}ms`;
}

const TRIGGER_BADGE_CLASS: Record<string, string> = {
  event: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300',
  manual: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
  schedule: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
};

export function TriggerBadge({
  triggerType,
  className = '',
}: {
  triggerType: string;
  className?: string;
}) {
  const cls =
    TRIGGER_BADGE_CLASS[triggerType] ??
    'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300';
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium capitalize ${cls} ${className}`}
      data-testid="hook-trigger-badge"
    >
      {triggerType}
    </span>
  );
}

export function triggerSummary(hook: Pick<Hook, 'trigger'>): string {
  const t = hook.trigger;
  if (t.type === 'manual') return 'Manual trigger';
  if (t.type === 'event') {
    const event = t.event ?? 'event';
    if (t.collection) return `${event} on ${t.collection}`;
    return event;
  }
  return t.type;
}

const EXEC_STATUS_CLASS: Record<string, string> = {
  success: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
  partial: 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300',
  failed: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
};

export function ExecutionStatusBadge({
  status,
}: {
  status: HookExecution['status'] | string;
}) {
  const cls =
    EXEC_STATUS_CLASS[status] ??
    'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300';
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium capitalize ${cls}`}
      data-testid="hook-execution-status"
    >
      {status}
    </span>
  );
}

/** Short summary of an action for list/overview cards. */
export function actionSummary(action: HookAction): string {
  switch (action.type) {
    case 'send_webhook': {
      const url = String(action.url ?? '');
      if (!url) return 'Webhook (no URL)';
      try {
        const host = new URL(url).host;
        return `Webhook → ${host}`;
      } catch {
        return `Webhook → ${url.slice(0, 40)}`;
      }
    }
    case 'send_email': {
      const to = String(action.to ?? '');
      return to ? `Email → ${to}` : 'Email (no recipient)';
    }
    case 'create_record':
      return `Create in ${String(action.collection || '…')}`;
    case 'update_record':
      return `Update ${String(action.collection || '…')}`;
    case 'delete_record':
      return `Delete from ${String(action.collection || '…')}`;
    case 'enqueue_job':
      return `Job: ${String(action.handler || '…')}`;
    default:
      return action.type;
  }
}

const ACTION_ACCENT: Record<string, string> = {
  send_webhook: 'border-l-blue-500',
  send_email: 'border-l-green-500',
  create_record: 'border-l-amber-500',
  update_record: 'border-l-amber-500',
  delete_record: 'border-l-amber-500',
  enqueue_job: 'border-l-indigo-500',
};

export function actionAccentClass(type: string): string {
  return ACTION_ACCENT[type] ?? 'border-l-muted-foreground';
}
