/**
 * Map instance GET /api/v1/auth/me onto the Studio auth store identity.
 *
 * `/me` returns { user_id, account_id, email, role }. Login returns nested
 * { user, account }. Platform Studio never logs in on the instance client, so
 * we accept both shapes.
 */

import {
  SYSTEM_ACCOUNT_CODE,
  SYSTEM_ACCOUNT_ID,
  SYSTEM_ACCOUNT_SLUG,
} from '@/lib/auth';
import type { AccountInfo, UserInfo } from '@/types/auth.types';

export interface InstanceMeLike {
  user?: Partial<UserInfo> | null;
  account?: Partial<AccountInfo> | null;
  user_id?: string;
  account_id?: string;
  email?: string;
  role?: string;
}

export interface InstanceIdentity {
  user: UserInfo;
  account: AccountInfo;
}

function isSystemAccountId(id: string): boolean {
  return id === SYSTEM_ACCOUNT_ID || id === SYSTEM_ACCOUNT_CODE;
}

export function instanceIdentityFromMe(
  me: InstanceMeLike | null | undefined,
): InstanceIdentity | null {
  if (!me) return null;
  const accountId = me.account?.id || me.account_id;
  const userId = me.user?.id || me.user_id;
  if (!accountId || !userId) return null;

  const system = isSystemAccountId(accountId);
  return {
    user: {
      id: userId,
      email: me.user?.email || me.email || '',
      role: me.user?.role || me.role || 'admin',
      is_active: me.user?.is_active ?? true,
      created_at: me.user?.created_at || '',
    },
    account: {
      id: accountId,
      slug: me.account?.slug || (system ? SYSTEM_ACCOUNT_SLUG : ''),
      name: me.account?.name || (system ? 'System' : ''),
      created_at: me.account?.created_at || '',
    },
  };
}
