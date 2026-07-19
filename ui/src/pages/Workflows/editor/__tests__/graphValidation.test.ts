import { describe, it, expect } from 'vitest';
import type { Edge } from '@xyflow/react';
import type { WorkflowStep } from '@/services/workflows.service';
import {
    validateStepNames,
    hasSelfEdges,
    validateGraphEdges,
} from '../graphValidation';

describe('validateStepNames', () => {
    it('returns null for unique non-empty names', () => {
        const steps: WorkflowStep[] = [
            { type: 'action', name: 'a' },
            { type: 'action', name: 'b' },
        ];
        expect(validateStepNames(steps)).toBeNull();
    });

    it('returns null for empty steps list', () => {
        expect(validateStepNames([])).toBeNull();
    });

    it('rejects empty names', () => {
        const steps: WorkflowStep[] = [
            { type: 'action', name: 'a' },
            { type: 'action', name: '  ' },
        ];
        expect(validateStepNames(steps)).toBe('All steps must have a name');
    });

    it('rejects duplicates', () => {
        const steps: WorkflowStep[] = [
            { type: 'action', name: 'same' },
            { type: 'action', name: 'same' },
        ];
        expect(validateStepNames(steps)).toBe('Step names must be unique');
    });
});

describe('self-edges', () => {
    it('detects self-edges', () => {
        const edges: Edge[] = [
            { id: '1', source: 'a', target: 'b' },
            { id: '2', source: 'c', target: 'c' },
        ];
        expect(hasSelfEdges(edges)).toBe(true);
        expect(validateGraphEdges(edges)).toBe('Self-edges are not allowed');
    });

    it('passes when no self-edges', () => {
        const edges: Edge[] = [{ id: '1', source: 'a', target: 'b' }];
        expect(hasSelfEdges(edges)).toBe(false);
        expect(validateGraphEdges(edges)).toBeNull();
    });
});
