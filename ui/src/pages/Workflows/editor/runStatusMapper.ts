/**
 * Map workflow instance step_logs onto canvas node runtime statuses.
 *
 * Executor step-log statuses: success | failed | skipped
 * Instance statuses: pending | running | waiting | completed | failed | cancelled
 * UI node statuses: pending | running | waiting | completed | failed | skipped
 */

import type { Node } from '@xyflow/react';
import type {
    WorkflowInstance,
    WorkflowStepLog,
} from '@/services/workflows.service';
import { TRIGGER_NODE_ID } from '../workflowConstants';
import {
    isStepNodeData,
    isTriggerNode,
    isTriggerNodeData,
    type NodeRunStatus,
} from './graphMapper';

export type { NodeRunStatus };

/** Normalize executor log status strings to UI node status. */
export function normalizeLogStatus(status: string): NodeRunStatus {
    const s = (status || '').toLowerCase();
    if (s === 'success' || s === 'completed') return 'completed';
    if (s === 'failed' || s === 'error') return 'failed';
    if (s === 'skipped') return 'skipped';
    if (s === 'running') return 'running';
    if (s === 'waiting') return 'waiting';
    if (s === 'pending') return 'pending';
    // Unknown → pending so we do not paint false failures
    return 'pending';
}

function logTimestamp(log: WorkflowStepLog): number {
    const raw = log.completed_at ?? log.started_at;
    if (!raw) return 0;
    const t = Date.parse(raw);
    return Number.isFinite(t) ? t : 0;
}

/**
 * Pick the latest log per step_name (by completed_at, then started_at).
 */
export function latestLogsByStepName(
    stepLogs: WorkflowStepLog[],
): Map<string, WorkflowStepLog> {
    const map = new Map<string, WorkflowStepLog>();
    for (const log of stepLogs) {
        const name = log.step_name;
        if (!name) continue;
        const prev = map.get(name);
        if (!prev || logTimestamp(log) >= logTimestamp(prev)) {
            map.set(name, log);
        }
    }
    return map;
}

/**
 * Build step_name → NodeRunStatus from logs + instance.current_step.
 * Does not include the synthetic trigger node.
 */
export function mapStepLogsToNodeStatus(
    stepLogs: WorkflowStepLog[],
    instance: Pick<WorkflowInstance, 'status' | 'current_step'>,
): Map<string, NodeRunStatus> {
    const latest = latestLogsByStepName(stepLogs);
    const result = new Map<string, NodeRunStatus>();

    for (const [name, log] of latest) {
        result.set(name, normalizeLogStatus(log.status));
    }

    const current = instance.current_step;
    if (current && (instance.status === 'running' || instance.status === 'waiting')) {
        // Live pointer overrides a prior log for the active step
        result.set(current, instance.status === 'waiting' ? 'waiting' : 'running');
    }

    return result;
}

/**
 * Merge run statuses into node data for styling.
 * - Step nodes without a map entry become `pending` when overlay is active.
 * - Trigger: `completed` once any step has a log or instance left pending; else unset.
 */
export function applyRunStatusToNodes(
    nodes: Node[],
    statusByName: Map<string, NodeRunStatus>,
    options?: { markMissingPending?: boolean },
): Node[] {
    const markPending = options?.markMissingPending ?? true;
    const hasAnyLog = statusByName.size > 0;

    return nodes.map((node) => {
        if (isTriggerNode(node)) {
            const triggerStatus: NodeRunStatus | null = hasAnyLog ? 'completed' : null;
            const data = isTriggerNodeData(node.data)
                ? { ...node.data, runStatus: triggerStatus }
                : { ...node.data, runStatus: triggerStatus };
            return { ...node, data };
        }

        if (!isStepNodeData(node.data)) {
            return node;
        }

        const fromMap = statusByName.get(node.id);
        const runStatus: NodeRunStatus | null =
            fromMap ?? (markPending ? 'pending' : null);

        return {
            ...node,
            data: {
                ...node.data,
                runStatus,
            },
        };
    });
}

/** Lookup latest log for a step node id (or null). */
export function getLogForNode(
    stepLogs: WorkflowStepLog[],
    nodeId: string,
): WorkflowStepLog | null {
    if (!nodeId || nodeId === TRIGGER_NODE_ID) return null;
    return latestLogsByStepName(stepLogs).get(nodeId) ?? null;
}
