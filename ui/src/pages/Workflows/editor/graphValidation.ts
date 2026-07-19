/**
 * Lightweight validation helpers for the workflow graph editor (Phase 1).
 */

import type { Edge } from '@xyflow/react';
import type { WorkflowStep } from '@/services/workflows.service';

/**
 * Validate step names are non-empty and unique.
 * @returns Error message or null if valid.
 */
export function validateStepNames(steps: WorkflowStep[]): string | null {
    const names = steps.map((s) => (s.name ?? '').trim());
    if (names.some((n) => !n)) {
        return 'All steps must have a name';
    }
    if (new Set(names).size !== names.length) {
        return 'Step names must be unique';
    }
    return null;
}

/** True if any edge connects a node to itself. */
export function hasSelfEdges(edges: Edge[]): boolean {
    return edges.some((e) => e.source === e.target);
}

/**
 * Collect self-edge issues for UI messaging.
 */
export function validateGraphEdges(edges: Edge[]): string | null {
    if (hasSelfEdges(edges)) {
        return 'Self-edges are not allowed';
    }
    return null;
}
