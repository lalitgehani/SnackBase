import { describe, it, expect, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { createElement, type ReactNode } from 'react';
import {
  InstanceClientProvider,
  useInstanceClient,
  InstanceClientProviderError,
} from '../InstanceClientProvider';

vi.mock('@/lib/config', () => ({
  IS_PLATFORM: false,
  loadConfig: () => ({
    apiBaseUrl: 'http://localhost:5173',
    platformPathPrefix: '/platform/v1',
    snackbaseUrl: 'http://localhost:8002',
    provisionApiUrl: 'http://localhost:8091',
  }),
  platformBaseUrl: (ref: string) => `http://localhost:5173/platform/v1/env/${ref}`,
}));

describe('InstanceClientProvider', () => {
  it('throws when useInstanceClient is used outside a provider', () => {
    expect(() => renderHook(() => useInstanceClient())).toThrow(InstanceClientProviderError);
  });

  it('does not export SnackBaseProvider or useSnackBase', async () => {
    const mod = await import('../InstanceClientProvider');
    expect(Object.keys(mod)).not.toContain('SnackBaseProvider');
    expect(Object.keys(mod)).not.toContain('useSnackBase');
  });

  it('constructs one self-host client with configured base URL', () => {
    const wrapper = ({ children }: { children: ReactNode }) =>
      createElement(InstanceClientProvider, null, children);

    const { result } = renderHook(() => useInstanceClient(), { wrapper });
    expect(result.current.getConfig().baseUrl).toBe('http://localhost:3000');
    expect(result.current.getConfig().storageBackend).toBe('localStorage');
  });

  it('returns the same client instance across re-renders', () => {
    const wrapper = ({ children }: { children: ReactNode }) =>
      createElement(InstanceClientProvider, null, children);

    const { result, rerender } = renderHook(() => useInstanceClient(), { wrapper });
    const first = result.current;
    rerender();
    expect(result.current).toBe(first);
  });
});
