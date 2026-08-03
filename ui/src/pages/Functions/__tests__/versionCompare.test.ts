import { describe, expect, it } from 'vitest';
import type { FunctionBody } from '@/services/functions.service';
import {
  compareFunctionVersions,
  firstInterestingFilePath,
  orderBodiesForCompare,
  parseUnifiedDiffLines,
  unifiedFileDiff,
} from '../versionCompare';

function body(
  overrides: Partial<FunctionBody> & Pick<FunctionBody, 'version' | 'version_id'>,
): FunctionBody {
  return {
    entrypoint: 'handler.py',
    files: { 'handler.py': 'print(1)\n' },
    dependencies: [],
    sha256: 'abc',
    ...overrides,
  };
}

describe('versionCompare', () => {
  it('orders bodies so left is older', () => {
    const v1 = body({ version: 1, version_id: 'a' });
    const v3 = body({ version: 3, version_id: 'b' });
    const [left, right] = orderBodiesForCompare(v3, v1);
    expect(left.version).toBe(1);
    expect(right.version).toBe(3);
  });

  it('detects added, removed, and changed files', () => {
    const older = body({
      version: 1,
      version_id: 'v1',
      files: {
        'handler.py': 'old\n',
        'gone.py': 'x\n',
      },
    });
    const newer = body({
      version: 2,
      version_id: 'v2',
      files: {
        'handler.py': 'new\n',
        'utils.py': 'y\n',
      },
    });
    const result = compareFunctionVersions(newer, older);
    expect(result.left.version).toBe(1);
    expect(result.right.version).toBe(2);
    expect(result.files).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ path: 'handler.py', status: 'changed' }),
        expect.objectContaining({ path: 'gone.py', status: 'removed' }),
        expect.objectContaining({ path: 'utils.py', status: 'added' }),
      ]),
    );
  });

  it('marks identical files unchanged and reports no interesting path preference over first', () => {
    const a = body({ version: 1, version_id: 'v1' });
    const b = body({ version: 2, version_id: 'v2' });
    const result = compareFunctionVersions(a, b);
    expect(result.files.every((f) => f.status === 'unchanged')).toBe(true);
    expect(firstInterestingFilePath(result.files)).toBe('handler.py');
  });

  it('diffs entrypoint and dependencies', () => {
    const older = body({
      version: 1,
      version_id: 'v1',
      entrypoint: 'handler.py',
      dependencies: ['cowsay==6.0', 'httpx==0.27.0'],
    });
    const newer = body({
      version: 2,
      version_id: 'v2',
      entrypoint: 'main.py',
      files: { 'main.py': 'pass\n' },
      dependencies: ['cowsay==6.1', 'httpx==0.27.0'],
    });
    const result = compareFunctionVersions(older, newer);
    expect(result.entrypointChanged).toBe(true);
    expect(result.depsAdded).toEqual(['cowsay==6.1']);
    expect(result.depsRemoved).toEqual(['cowsay==6.0']);
  });

  it('prefers first changed/added/removed file', () => {
    const result = compareFunctionVersions(
      body({
        version: 1,
        version_id: 'v1',
        files: { 'a.py': '1\n', 'b.py': 'same\n' },
      }),
      body({
        version: 2,
        version_id: 'v2',
        files: { 'a.py': '2\n', 'b.py': 'same\n' },
      }),
    );
    expect(firstInterestingFilePath(result.files)).toBe('a.py');
  });

  it('builds a unified patch with added and removed lines', () => {
    const result = compareFunctionVersions(
      body({
        version: 1,
        version_id: 'v1',
        files: { 'handler.py': 'print(1)\n' },
      }),
      body({
        version: 2,
        version_id: 'v2',
        files: { 'handler.py': 'print(2)\n' },
      }),
    );
    const file = result.files.find((f) => f.path === 'handler.py')!;
    const patch = unifiedFileDiff(file);
    expect(patch).toContain('-print(1)');
    expect(patch).toContain('+print(2)');
    const lines = parseUnifiedDiffLines(patch);
    expect(lines.some((l) => l.type === 'removed')).toBe(true);
    expect(lines.some((l) => l.type === 'added')).toBe(true);
  });

  it('returns empty unified diff for unchanged files', () => {
    const file = {
      path: 'handler.py',
      status: 'unchanged' as const,
      leftContent: 'x\n',
      rightContent: 'x\n',
    };
    expect(unifiedFileDiff(file)).toBe('');
  });
});
