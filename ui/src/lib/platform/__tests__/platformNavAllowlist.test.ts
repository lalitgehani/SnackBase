import { describe, expect, it } from 'vitest';
import {
  filterStudioNavItems,
  isPlatformHiddenStudioRoute,
  PLATFORM_HIDDEN_STUDIO_ROUTES,
} from '@/lib/platform/platformNavAllowlist';

describe('platformNavAllowlist', () => {
  it('excludes superadmin-only accounts route in platform mode', () => {
    const items = [{ url: '/admin/accounts', title: 'Accounts' }, { url: '/admin/users', title: 'Users' }];
    const filtered = filterStudioNavItems(items, true);
    expect(filtered.map((i) => i.url)).toEqual(['/admin/users']);
  });

  it('includes all routes in self-host mode', () => {
    const items = [{ url: '/admin/accounts', title: 'Accounts' }];
    expect(filterStudioNavItems(items, false)).toHaveLength(1);
  });

  it('documents hidden routes', () => {
    expect(PLATFORM_HIDDEN_STUDIO_ROUTES).toContain('/admin/accounts');
    expect(isPlatformHiddenStudioRoute('/admin/accounts')).toBe(true);
  });
});
