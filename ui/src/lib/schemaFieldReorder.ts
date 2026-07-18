/**
 * Pure helpers for schema field reordering (buttons + drag-and-drop).
 */

import type { FieldDefinition } from '@/services/collections.service';

/**
 * Whether a field at `index` may move in the given direction.
 * In edit mode (`originalFieldCount > 0`), only newly added fields may reorder
 * among themselves — never past locked existing fields.
 */
export function canMoveField(
  fieldsLength: number,
  index: number,
  direction: 'up' | 'down',
  originalFieldCount = 0,
): boolean {
  const target = direction === 'up' ? index - 1 : index + 1;
  if (target < 0 || target >= fieldsLength) return false;
  if (originalFieldCount > 0) {
    if (index < originalFieldCount || target < originalFieldCount) return false;
  }
  return true;
}

/**
 * Move a field one step up or down. Returns the same array reference if the
 * move is not allowed.
 */
export function moveFieldByDirection(
  fields: FieldDefinition[],
  index: number,
  direction: 'up' | 'down',
  originalFieldCount = 0,
): FieldDefinition[] {
  if (!canMoveField(fields.length, index, direction, originalFieldCount)) {
    return fields;
  }
  const targetIndex = direction === 'up' ? index - 1 : index + 1;
  const next = [...fields];
  ;[next[index], next[targetIndex]] = [next[targetIndex], next[index]];
  return next;
}

/**
 * Reorder by moving the item at `fromIndex` to `toIndex` (array splice).
 * Returns the same array reference if the move is not allowed.
 *
 * Edit mode: both from and to must be in the new-fields range
 * (`>= originalFieldCount`).
 */
export function reorderFields(
  fields: FieldDefinition[],
  fromIndex: number,
  toIndex: number,
  originalFieldCount = 0,
): FieldDefinition[] {
  if (
    fromIndex === toIndex ||
    fromIndex < 0 ||
    toIndex < 0 ||
    fromIndex >= fields.length ||
    toIndex >= fields.length
  ) {
    return fields;
  }

  if (originalFieldCount > 0) {
    if (fromIndex < originalFieldCount || toIndex < originalFieldCount) {
      return fields;
    }
  }

  const next = [...fields];
  const [removed] = next.splice(fromIndex, 1);
  next.splice(toIndex, 0, removed);
  return next;
}

/**
 * Remap a set of expanded row indices after a swap of two indices.
 */
export function remapExpandedAfterSwap(
  expanded: Set<number>,
  indexA: number,
  indexB: number,
): Set<number> {
  const next = new Set(expanded);
  const a = expanded.has(indexA);
  const b = expanded.has(indexB);
  if (a) next.add(indexB);
  else next.delete(indexB);
  if (b) next.add(indexA);
  else next.delete(indexA);
  return next;
}

/**
 * Remap expanded indices after a splice reorder (from → to).
 */
export function remapExpandedAfterReorder(
  expanded: Set<number>,
  fromIndex: number,
  toIndex: number,
): Set<number> {
  if (fromIndex === toIndex) return expanded;
  const next = new Set<number>();
  for (const i of expanded) {
    let ni = i;
    if (i === fromIndex) {
      ni = toIndex;
    } else if (fromIndex < toIndex && i > fromIndex && i <= toIndex) {
      ni = i - 1;
    } else if (fromIndex > toIndex && i >= toIndex && i < fromIndex) {
      ni = i + 1;
    }
    next.add(ni);
  }
  return next;
}
