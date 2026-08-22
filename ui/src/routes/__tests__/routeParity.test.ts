import { describe, expect, it } from 'vitest';
import { ADMIN_STUDIO_ROUTE_SUFFIXES } from '@/routes/routeParity';

describe('route parity', () => {
  it('maps every self-host admin suffix to a platform project route', () => {
    for (const suffix of ADMIN_STUDIO_ROUTE_SUFFIXES) {
      expect(suffix.startsWith('/')).toBe(false);
      expect(`/project/:ref/${suffix}`.includes(':ref')).toBe(true);
    }
    expect(ADMIN_STUDIO_ROUTE_SUFFIXES).toContain('dashboard');
    expect(ADMIN_STUDIO_ROUTE_SUFFIXES).toContain('collections');
  });
});
