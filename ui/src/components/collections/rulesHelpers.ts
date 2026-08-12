/**
 * Helpers for collection access-rule draft comparison and status display.
 * Semantics match authorization middleware:
 * - null → locked (403 for non-superadmin)
 * - "" → unrestricted for authenticated users
 * - non-empty → custom expression (auth required)
 *
 * Unauthenticated access additionally requires `allow_anonymous`: an empty rule
 * says "no restriction for my users", and anonymous callers pick their tenant
 * with the X-Account-ID header, so exposing a collection to them is a separate
 * decision (M-08).
 */

import type { CollectionRule } from '@/services/collections.service';

export type RuleOperationKey =
  | 'list_rule'
  | 'view_rule'
  | 'create_rule'
  | 'update_rule'
  | 'delete_rule';

export type FieldPermissionKey =
  | 'list_fields'
  | 'view_fields'
  | 'create_fields'
  | 'update_fields';

export const RULE_OPERATIONS: { key: RuleOperationKey; label: string }[] = [
  { key: 'list_rule', label: 'List' },
  { key: 'view_rule', label: 'View' },
  { key: 'create_rule', label: 'Create' },
  { key: 'update_rule', label: 'Update' },
  { key: 'delete_rule', label: 'Delete' },
];

/** Snapshot of rule fields used for dirty comparison and saves. */
export interface RulesSnapshot {
  allow_anonymous: boolean;
  list_rule: string | null;
  view_rule: string | null;
  create_rule: string | null;
  update_rule: string | null;
  delete_rule: string | null;
  list_fields: string;
  view_fields: string;
  create_fields: string;
  update_fields: string;
}

export function toRulesSnapshot(
  rules: Pick<CollectionRule, keyof RulesSnapshot>,
): RulesSnapshot {
  return {
    allow_anonymous: rules.allow_anonymous,
    list_rule: rules.list_rule,
    view_rule: rules.view_rule,
    create_rule: rules.create_rule,
    update_rule: rules.update_rule,
    delete_rule: rules.delete_rule,
    list_fields: rules.list_fields,
    view_fields: rules.view_fields,
    create_fields: rules.create_fields,
    update_fields: rules.update_fields,
  };
}

/** Stable string for dirty comparison. */
export function normalizeRulesForCompare(rules: RulesSnapshot): string {
  return JSON.stringify(toRulesSnapshot(rules));
}

export function isRulesDirty(
  draft: RulesSnapshot,
  baseline: RulesSnapshot,
): boolean {
  return normalizeRulesForCompare(draft) !== normalizeRulesForCompare(baseline);
}

/** Operations with no rule — unrestricted for authenticated users. */
export function getPublicOperations(rules: RulesSnapshot): string[] {
  return RULE_OPERATIONS.filter(({ key }) => rules[key] === '').map(
    ({ label }) => label,
  );
}

/** Operations actually reachable without authentication. */
export function getAnonymousOperations(rules: RulesSnapshot): string[] {
  return rules.allow_anonymous ? getPublicOperations(rules) : [];
}

export function getLockedOperations(rules: RulesSnapshot): string[] {
  return RULE_OPERATIONS.filter(({ key }) => rules[key] === null).map(
    ({ label }) => label,
  );
}

export function getCustomOperations(rules: RulesSnapshot): string[] {
  return RULE_OPERATIONS.filter(({ key }) => {
    const v = rules[key];
    return v !== null && v !== '';
  }).map(({ label }) => label);
}
