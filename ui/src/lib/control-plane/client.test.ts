import { describe, expect, it } from 'vitest';
import { getControlPlaneClient, resetControlPlaneClientForTests } from '@/lib/control-plane/client';

describe('control-plane client', () => {
  it('exports a single memoized instance per page load', () => {
    resetControlPlaneClientForTests();
    const a = getControlPlaneClient();
    const b = getControlPlaneClient();
    expect(a).toBe(b);
  });
});
