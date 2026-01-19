/**
 * OAuth callback page
 * Handles the callback from OAuth providers in the popup window
 * Passes the result back to the parent window via postMessage
 */

import { useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router';
import { apiClient } from '@/lib/api';

export default function OAuthCallback() {
  const [searchParams] = useSearchParams();
  const hasProcessed = useRef(false);

  useEffect(() => {
    // Guard against React Strict Mode double execution
    if (hasProcessed.current) {
      return;
    }
    hasProcessed.current = true;

    const handleCallback = async () => {
      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const provider = searchParams.get('provider') || 'google';
      const error = searchParams.get('error');

      if (error) {
        // Pass error back to parent window
        window.opener?.postMessage(
          {
            type: 'oauth_callback',
            error: error || 'OAuth authentication failed',
          },
          window.location.origin
        );
        window.close();
        return;
      }

      if (!code || !state) {
        window.opener?.postMessage(
          {
            type: 'oauth_callback',
            error: 'Missing authorization code or state',
          },
          window.location.origin
        );
        window.close();
        return;
      }

      try {
        // Exchange code for tokens
        const response = await apiClient.post(`/auth/oauth/${provider}/callback`, {
          code,
          state,
          redirect_uri: `${window.location.origin}/oauth/callback`,
        });

        // Pass successful result back to parent window
        window.opener?.postMessage(
          {
            type: 'oauth_callback',
            ...response.data,
          },
          window.location.origin
        );

        // Close popup after a short delay to ensure message is delivered
        setTimeout(() => {
          window.close();
        }, 100);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'OAuth callback failed';
        window.opener?.postMessage(
          {
            type: 'oauth_callback',
            error: errorMessage,
          },
          window.location.origin
        );
        window.close();
      }
    };

    handleCallback();
  }, [searchParams]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
        <p className="mt-4 text-gray-600">Completing sign-in...</p>
      </div>
    </div>
  );
}
