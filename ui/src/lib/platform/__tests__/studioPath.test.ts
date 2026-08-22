import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { normalizeToAdminPath } from '@/lib/platform/studioPath';

describe('studioPath', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_IS_PLATFORM', 'false');
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('maps admin routes in self-host mode', async () => {
    vi.resetModules();
    const mod = await import('@/lib/platform/studioPath');
    expect(mod.studioPath('/collections')).toBe('/admin/collections');
    expect(mod.studioPath('/admin/dashboard')).toBe('/admin/dashboard');
  });

  it('normalizes project paths to admin paths', () => {
    expect(normalizeToAdminPath('/project/prod/collections')).toBe('/admin/collections');
    expect(normalizeToAdminPath('/admin/users')).toBe('/admin/users');
  });
});

describe('studioPath platform mode', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_IS_PLATFORM', 'true');
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('maps admin routes to project paths', async () => {
    vi.resetModules();
    const mod = await import('@/lib/platform/studioPath');
    expect(mod.studioPath('/admin/collections', 'prod')).toBe('/project/prod/collections');
  });
});
