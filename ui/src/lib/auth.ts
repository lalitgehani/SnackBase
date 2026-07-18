/**
 * Auth helpers shared across the admin UI.
 *
 * Backend superadmin check (require_superadmin): account_id === SYSTEM_ACCOUNT_ID.
 * Superadmin users are seeded with the "admin" role name on the system account —
 * not a distinct role named "superadmin".
 */

/** Nil UUID primary key of the SnackBase system account (backend SYSTEM_ACCOUNT_ID). */
export const SYSTEM_ACCOUNT_ID = '00000000-0000-0000-0000-000000000000';

/** Human-readable system account code (login identifier / account_code). */
export const SYSTEM_ACCOUNT_CODE = 'SY0000';

/** System account slug. */
export const SYSTEM_ACCOUNT_SLUG = 'system';

export interface AccountLike {
  id?: string | null;
  slug?: string | null;
}

/**
 * True when the given account is the SnackBase system account (superadmin tenant).
 * Matches backend require_superadmin: membership of the system account.
 */
export function isSuperadminAccount(
  account: AccountLike | null | undefined,
): boolean {
  if (!account) return false;
  return (
    account.id === SYSTEM_ACCOUNT_ID ||
    account.id === SYSTEM_ACCOUNT_CODE ||
    account.slug === SYSTEM_ACCOUNT_SLUG
  );
}
