import { createTwoFilesPatch } from 'diff';
import type { FunctionBody } from '@/services/functions.service';

export type FileDiffStatus = 'added' | 'removed' | 'changed' | 'unchanged';

export interface ComparedFile {
  path: string;
  status: FileDiffStatus;
  leftContent: string | null;
  rightContent: string | null;
}

export interface VersionCompareResult {
  left: FunctionBody;
  right: FunctionBody;
  entrypointChanged: boolean;
  depsAdded: string[];
  depsRemoved: string[];
  files: ComparedFile[];
}

/** Order so left is the older version and right is the newer. */
export function orderBodiesForCompare(
  a: FunctionBody,
  b: FunctionBody,
): [FunctionBody, FunctionBody] {
  return a.version <= b.version ? [a, b] : [b, a];
}

export function compareFunctionVersions(
  a: FunctionBody,
  b: FunctionBody,
): VersionCompareResult {
  const [left, right] = orderBodiesForCompare(a, b);
  const leftDeps = new Set(left.dependencies ?? []);
  const rightDeps = new Set(right.dependencies ?? []);
  const depsAdded = [...rightDeps].filter((d) => !leftDeps.has(d)).sort();
  const depsRemoved = [...leftDeps].filter((d) => !rightDeps.has(d)).sort();

  const paths = new Set([
    ...Object.keys(left.files ?? {}),
    ...Object.keys(right.files ?? {}),
  ]);
  const files: ComparedFile[] = [...paths]
    .sort((x, y) => x.localeCompare(y))
    .map((path) => {
      const leftContent = Object.prototype.hasOwnProperty.call(left.files, path)
        ? left.files[path]
        : null;
      const rightContent = Object.prototype.hasOwnProperty.call(right.files, path)
        ? right.files[path]
        : null;
      let status: FileDiffStatus;
      if (leftContent === null && rightContent !== null) status = 'added';
      else if (leftContent !== null && rightContent === null) status = 'removed';
      else if (leftContent !== rightContent) status = 'changed';
      else status = 'unchanged';
      return { path, status, leftContent, rightContent };
    });

  return {
    left,
    right,
    entrypointChanged: left.entrypoint !== right.entrypoint,
    depsAdded,
    depsRemoved,
    files,
  };
}

export function firstInterestingFilePath(files: ComparedFile[]): string | null {
  const interesting = files.find((f) => f.status !== 'unchanged');
  return interesting?.path ?? files[0]?.path ?? null;
}

/** Unified patch for one file path (empty string when identical). */
export function unifiedFileDiff(file: ComparedFile): string {
  if (file.status === 'unchanged') return '';
  const oldStr = file.leftContent ?? '';
  const newStr = file.rightContent ?? '';
  return createTwoFilesPatch(
    file.path,
    file.path,
    oldStr,
    newStr,
    undefined,
    undefined,
    { context: 3 },
  );
}

export interface DiffLine {
  type: 'header' | 'hunk' | 'added' | 'removed' | 'context' | 'meta';
  text: string;
}

/** Split a unified patch into typed lines for rendering. */
export function parseUnifiedDiffLines(patch: string): DiffLine[] {
  if (!patch) return [];
  return patch.split('\n').map((text) => {
    if (text.startsWith('diff ') || text.startsWith('index ')) {
      return { type: 'meta' as const, text };
    }
    if (text.startsWith('---') || text.startsWith('+++')) {
      return { type: 'header' as const, text };
    }
    if (text.startsWith('@@')) {
      return { type: 'hunk' as const, text };
    }
    if (text.startsWith('+')) {
      return { type: 'added' as const, text };
    }
    if (text.startsWith('-')) {
      return { type: 'removed' as const, text };
    }
    return { type: 'context' as const, text };
  });
}

