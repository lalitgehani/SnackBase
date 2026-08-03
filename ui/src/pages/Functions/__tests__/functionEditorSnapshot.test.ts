import { describe, expect, it } from 'vitest';
import {
  createEditorSnapshot,
  isEditorDirty,
  snapshotsEqual,
} from '../functionEditorSnapshot';

describe('functionEditorSnapshot', () => {
  it('marks a freshly loaded snapshot clean against itself', () => {
    const snap = createEditorSnapshot(
      { 'handler.py': 'x = 1\n', 'requirements.txt': 'cowsay==6.1\n' },
      ['cowsay==6.1'],
      'handler.py',
    );
    expect(isEditorDirty(snap, snap)).toBe(false);
  });

  it('marks dirty when a single character changes', () => {
    const baseline = createEditorSnapshot(
      { 'handler.py': 'x = 1\n' },
      [],
      'handler.py',
    );
    const current = createEditorSnapshot(
      { 'handler.py': 'x = 2\n' },
      [],
      'handler.py',
    );
    expect(isEditorDirty(current, baseline)).toBe(true);
  });

  it('clears dirty when reverted to baseline', () => {
    const baseline = createEditorSnapshot(
      { 'handler.py': 'x = 1\n', 'utils.py': 'y\n' },
      ['httpx==0.28.0'],
      'handler.py',
    );
    const edited = createEditorSnapshot(
      { 'handler.py': 'x = 9\n', 'utils.py': 'y\n' },
      ['httpx==0.28.0'],
      'handler.py',
    );
    expect(isEditorDirty(edited, baseline)).toBe(true);
    expect(isEditorDirty(baseline, baseline)).toBe(false);
  });

  it('treats dependency and entrypoint changes as dirty', () => {
    const baseline = createEditorSnapshot({ 'handler.py': 'x\n' }, [], 'handler.py');
    expect(
      isEditorDirty(
        createEditorSnapshot({ 'handler.py': 'x\n' }, ['cowsay==6.1'], 'handler.py'),
        baseline,
      ),
    ).toBe(true);
    expect(
      isEditorDirty(
        createEditorSnapshot(
          { 'handler.py': 'x\n', 'utils.py': '' },
          [],
          'utils.py',
        ),
        createEditorSnapshot(
          { 'handler.py': 'x\n', 'utils.py': '' },
          [],
          'handler.py',
        ),
      ),
    ).toBe(true);
  });

  it('normalizes requirements.txt from dependencies', () => {
    const a = createEditorSnapshot({ 'handler.py': 'x' }, [' cowsay == 6.1 '], 'handler.py');
    const b = createEditorSnapshot(
      { 'handler.py': 'x', 'requirements.txt': 'stale==1.0\n' },
      ['cowsay==6.1'],
      'handler.py',
    );
    expect(snapshotsEqual(a, b)).toBe(true);
    expect(a.files['requirements.txt']).toBe('cowsay==6.1\n');
  });
});
