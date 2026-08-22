import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { createElement, type ReactNode } from 'react';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { SYSTEM_ACCOUNT_ID } from '@/lib/auth';

const ENV_REF = 'abcdefghijklmnopqrst';

describe('InstanceClientProvider (platform mode)', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_IS_PLATFORM', 'true');
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('hydrates the instance auth store as the system-account operator', async () => {
    vi.resetModules();

    server.use(
      http.get(/\/api\/v1\/auth\/me$/, () =>
        HttpResponse.json({
          user_id: 'admin-sub',
          account_id: SYSTEM_ACCOUNT_ID,
          email: 'admin@platform.example.com',
          role: 'admin',
        }),
      ),
    );

    const { InstanceClientProvider, useInstanceClient } = await import(
      '../InstanceClientProvider'
    );
    const { useAuthStore } = await import('@/stores/auth.store');
    const { isSuperadminAccount } = await import('@/lib/auth');

    useAuthStore.setState({
      user: null,
      account: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    });

    const getAccessToken = () => 'platform-jwt';
    const wrapper = ({ children }: { children: ReactNode }) =>
      createElement(
        InstanceClientProvider,
        { envRef: ENV_REF, getAccessToken },
        children,
      );

    const { result } = renderHook(() => useInstanceClient(), { wrapper });
    expect(result.current.getConfig().storageBackend).toBe('memory');
    expect(result.current.getConfig().baseUrl).toContain(`/env/${ENV_REF}`);

    await waitFor(() => {
      const { account, user, isAuthenticated } = useAuthStore.getState();
      expect(isSuperadminAccount(account)).toBe(true);
      expect(isAuthenticated).toBe(true);
      expect(user?.email).toBe('admin@platform.example.com');
    });
  });
});
