/**
 * Summary / validation helpers for canvas card subtitles.
 */

import type { WorkflowStep, WorkflowTriggerConfig } from '@/services/workflows.service';
import { triggerSummary } from '../graphMapper';
import { ACTION_TYPES } from '../../workflowConstants';

export function actionTypeLabel(actionType: unknown): string {
    const v = String(actionType ?? '');
    return ACTION_TYPES.find((a) => a.value === v)?.label ?? (v || 'Action');
}

export function stepSubtitle(step: WorkflowStep): string {
    switch (step.type) {
        case 'action':
            return actionTypeLabel(step.action_type);
        case 'condition':
            return String(step.expression || 'No expression');
        case 'wait_delay':
            return String(step.duration || '—');
        case 'wait_condition':
            return String(step.expression || 'No expression');
        case 'wait_event':
            return String(step.event || 'event');
        case 'loop': {
            const items = String(step.items || '');
            return items ? truncate(items, 36) : 'No items';
        }
        case 'parallel': {
            const branches = step.branches;
            const n = Array.isArray(branches) ? branches.length : 0;
            return n === 1 ? '1 branch' : `${n} branches`;
        }
        default:
            return String(step.type || 'step');
    }
}

export function stepBadge(step: WorkflowStep): string | undefined {
    switch (step.type) {
        case 'action':
            return String(step.action_type ?? 'action');
        case 'condition':
            return 'condition';
        case 'wait_delay':
            return 'delay';
        case 'wait_condition':
            return 'wait until';
        case 'wait_event':
            return 'wait event';
        case 'loop':
            return 'loop';
        case 'parallel':
            return 'parallel';
        default:
            return step.type;
    }
}

export function isStepInvalid(step: WorkflowStep): boolean {
    if (!step.name || !String(step.name).trim()) return true;
    switch (step.type) {
        case 'action':
            return !step.action_type;
        case 'condition':
            return !String(step.expression ?? '').trim();
        case 'wait_delay':
            return !String(step.duration ?? '').trim();
        case 'wait_condition':
            return !String(step.expression ?? '').trim();
        case 'wait_event':
            return !String(step.event ?? '').trim();
        case 'loop':
            return !String(step.items ?? '').trim();
        case 'parallel':
            return false;
        default:
            return false;
    }
}

export function triggerSubtitle(trigger: WorkflowTriggerConfig): string {
    return triggerSummary(trigger);
}

function truncate(s: string, max: number): string {
    if (s.length <= max) return s;
    return `${s.slice(0, max - 1)}…`;
}
