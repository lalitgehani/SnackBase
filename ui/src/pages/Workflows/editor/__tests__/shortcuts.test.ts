import { describe, it, expect } from 'vitest';
import { isEditableKeyboardTarget } from '../useWorkflowEditorShortcuts';

describe('isEditableKeyboardTarget', () => {
    it('returns true for input/textarea/select', () => {
        const input = document.createElement('input');
        const textarea = document.createElement('textarea');
        const select = document.createElement('select');
        expect(isEditableKeyboardTarget(input)).toBe(true);
        expect(isEditableKeyboardTarget(textarea)).toBe(true);
        expect(isEditableKeyboardTarget(select)).toBe(true);
    });

    it('returns true for contenteditable', () => {
        const div = document.createElement('div');
        div.contentEditable = 'true';
        expect(isEditableKeyboardTarget(div)).toBe(true);
    });

    it('returns false for body / plain div', () => {
        expect(isEditableKeyboardTarget(document.body)).toBe(false);
        expect(isEditableKeyboardTarget(document.createElement('div'))).toBe(false);
    });

    it('returns false for null', () => {
        expect(isEditableKeyboardTarget(null)).toBe(false);
    });
});
