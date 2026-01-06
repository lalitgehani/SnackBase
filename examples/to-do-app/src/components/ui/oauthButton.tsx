/**
 * Google OAuth sign-in button component
 */

import { useState } from 'react';
import { useAuthStore } from '@/stores/auth.store';
import { Loader2 } from 'lucide-react';

interface OAuthButtonProps {
  provider?: 'google' | 'github' | 'microsoft' | 'apple';
  account?: string;
  accountName?: string;
  onSuccess?: () => void;
  onError?: (error: string) => void;
}

const PROVIDER_CONFIG = {
  google: {
    label: 'Google',
    icon: (
      <svg className="w-5 h-5" viewBox="0 0 24 24">
        <path
          fill="#4285F4"
          d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
        />
        <path
          fill="#34A853"
          d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
        />
        <path
          fill="#FBBC05"
          d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
        />
        <path
          fill="#EA4335"
          d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
        />
      </svg>
    ),
  },
  github: {
    label: 'GitHub',
    icon: (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
        <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
      </svg>
    ),
  },
  microsoft: {
    label: 'Microsoft',
    icon: (
      <svg className="w-5 h-5" viewBox="0 0 24 24">
        <path fill="#f3f3f3" d="M0 0h24v24H0z" />
        <path fill="#f35325" d="M1 1h10v10H1z" />
        <path fill="#81bc06" d="M13 1h10v10H13z" />
        <path fill="#05a6f0" d="M1 13h10v10H1z" />
        <path fill="#ffba08" d="M13 13h10v10H13z" />
      </svg>
    ),
  },
  apple: {
    label: 'Apple',
    icon: (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
        <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31 1.05-2.17 2.66-4.22 2.68-1.99.03-3.54-2.17-5.43-4.52-2.96-3.65-2.63-10.23.71-12.53 1.48-1.06 3.64-.94 4.96.02 1.31.95 2.32.96 3.81.02 1.49-.94 2.92-.95 4.35-.02 1.43.93 2.83.95 4.28.02 1.45-.93 2.86-.96 4.28-.01z" />
      </svg>
    ),
  },
};

export default function OAuthButton({
  provider = 'google',
  account,
  accountName,
  onSuccess,
  onError,
}: OAuthButtonProps) {
  const { oauthLogin, isLoading } = useAuthStore();
  const [isPending, setIsPending] = useState(false);

  const config = PROVIDER_CONFIG[provider];

  const handleClick = async () => {
    setIsPending(true);
    try {
      await oauthLogin(provider, account, accountName);
      onSuccess?.();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'OAuth sign-in failed';
      onError?.(errorMessage);
    } finally {
      setIsPending(false);
    }
  };

  const isDisabled = isLoading || isPending;

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={isDisabled}
      className="w-full flex items-center justify-center gap-3 px-4 py-2.5 border border-gray-300 rounded-md bg-white text-gray-700 font-medium hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
    >
      {isPending ? (
        <Loader2 className="w-5 h-5 animate-spin" />
      ) : (
        config.icon
      )}
      <span>Continue with {config.label}</span>
    </button>
  );
}
