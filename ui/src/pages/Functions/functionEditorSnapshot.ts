import {
  generateRequirementsTxt,
  normalizeDependencies,
} from './functionSourceUtils';

export interface FunctionEditorSnapshot {
  files: Record<string, string>;
  dependencies: string[];
  entrypoint: string;
}

/**
 * Normalize files + deps + entrypoint for dirty comparison.
 * Paths are sorted; requirements.txt is always regenerated from deps.
 */
export function createEditorSnapshot(
  files: Record<string, string>,
  dependencies: string[],
  entrypoint: string,
): FunctionEditorSnapshot {
  const deps = normalizeDependencies(dependencies);
  const normalizedFiles: Record<string, string> = {};
  for (const key of Object.keys(files).sort()) {
    if (key === 'requirements.txt') continue;
    normalizedFiles[key] = files[key] ?? '';
  }
  normalizedFiles['requirements.txt'] = generateRequirementsTxt(deps);
  return {
    files: normalizedFiles,
    dependencies: deps,
    entrypoint,
  };
}

export function snapshotsEqual(
  a: FunctionEditorSnapshot,
  b: FunctionEditorSnapshot,
): boolean {
  if (a.entrypoint !== b.entrypoint) return false;
  if (a.dependencies.length !== b.dependencies.length) return false;
  if (a.dependencies.some((d, i) => d !== b.dependencies[i])) return false;
  const aKeys = Object.keys(a.files);
  const bKeys = Object.keys(b.files);
  if (aKeys.length !== bKeys.length) return false;
  for (const key of aKeys) {
    if ((a.files[key] ?? '') !== (b.files[key] ?? '')) return false;
  }
  return true;
}

export function isEditorDirty(
  current: FunctionEditorSnapshot,
  baseline: FunctionEditorSnapshot | null,
): boolean {
  if (!baseline) return false;
  return !snapshotsEqual(current, baseline);
}
