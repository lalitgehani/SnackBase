import { describe, expect, it } from 'vitest';
import { isSuperadminAccount, SYSTEM_ACCOUNT_ID } from '@/lib/auth';
import { instanceIdentityFromMe } from '../instanceIdentity';

describe('instanceIdentityFromMe', () => {
  it('maps /auth/me onto the system account so isSuperadmin is true', () => {
    const identity = instanceIdentityFromMe({
      user_id: 'admin-sub',
      account_id: SYSTEM_ACCOUNT_ID,
      email: 'admin@platform.example.com',
      role: 'admin',
    });
    expect(identity).not.toBeNull();
    expect(isSuperadminAccount(identity?.account)).toBe(true);
    expect(identity?.user.email).toBe('admin@platform.example.com');
    expect(identity?.account.slug).toBe('system');
  });

  it('prefers nested login-shaped user/account objects', () => {
    const identity = instanceIdentityFromMe({
      user: {
        id: 'user-1',
        email: 'admin@example.com',
        role: 'admin',
        is_active: true,
        created_at: '2026-01-01T00:00:00Z',
      },
      account: {
        id: SYSTEM_ACCOUNT_ID,
        slug: 'system',
        name: 'System',
        created_at: '2026-01-01T00:00:00Z',
      },
    });
    expect(isSuperadminAccount(identity?.account)).toBe(true);
    expect(identity?.user.id).toBe('user-1');
  });

  it('returns null when account_id is missing (token present but no identity)', () => {
    expect(
      instanceIdentityFromMe({
        user_id: 'admin-sub',
        email: 'admin@platform.example.com',
        role: 'admin',
      }),
    ).toBeNull();
  });

  it('does not treat a tenant account as superadmin', () => {
    const identity = instanceIdentityFromMe({
      user_id: 'user-1',
      account_id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
      email: 'owner@acme.example.com',
      role: 'admin',
    });
    expect(isSuperadminAccount(identity?.account)).toBe(false);
  });
});
