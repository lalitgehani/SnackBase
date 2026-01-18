/**
 * OAuth service
 * Handles Google OAuth flow for authentication
 */

import { apiClient } from '@/lib/api';
import type {
  OAuthAuthorizeResponse,
  OAuthCallbackResponse,
} from '@/types';

const OAUTH_CALLBACK_URL = `${window.location.origin}/oauth/callback`;

/**
 * Initiate OAuth authorization flow
 * Opens a popup window for Google sign-in
 */
export const initiateOAuth = async (
  provider: 'google' | 'github' | 'microsoft' | 'apple' = 'google'
): Promise<{ url: string; state: string }> => {
  const response = await apiClient.post<OAuthAuthorizeResponse>(
    `/auth/oauth/${provider}/authorize`,
    {
      redirect_uri: OAUTH_CALLBACK_URL,
    }
  );

  return {
    url: response.data.authorization_url,
    state: response.data.state,
  };
};

/**
 * Exchange OAuth code for tokens
 * Called after user approves in the popup
 */
export const oauthCallback = async (
  provider: 'google' | 'github' | 'microsoft' | 'apple' = 'google',
  code: string,
  state: string
): Promise<OAuthCallbackResponse> => {
  const response = await apiClient.post<OAuthCallbackResponse>(
    `/auth/oauth/${provider}/callback`,
    {
      code,
      state,
      redirect_uri: OAUTH_CALLBACK_URL,
    }
  );

  return response.data;
};

/**
 * Complete OAuth flow using popup window
 * Returns auth response or throws error
 */
export const signInWithOAuth = async (
  provider: 'google' | 'github' | 'microsoft' | 'apple' = 'google'
): Promise<OAuthCallbackResponse> => {
  // Step 1: Get authorization URL
  const { url } = await initiateOAuth(provider);

  // Step 2: Open popup window
  const popup = window.open(
    url,
    'OAuth Sign In',
    'width=500,height=600,scrollbars=yes,resizable=yes'
  );

  if (!popup) {
    throw new Error('Failed to open popup. Please allow popups for this site.');
  }

  // Step 3: Wait for callback via message event
  return new Promise((resolve, reject) => {
    const messageHandler = (event: MessageEvent) => {
      // Verify origin for security
      if (event.origin !== window.location.origin) {
        return;
      }

      // Check if this is our OAuth callback message
      if (event.data.type === 'oauth_callback') {
        // Clean up
        window.removeEventListener('message', messageHandler);
        popup.close();

        if (event.data.error) {
          reject(new Error(event.data.error));
        } else {
          resolve(event.data as OAuthCallbackResponse);
        }
      }
    };

    window.addEventListener('message', messageHandler);

    // Check if popup was closed manually
    const checkClosed = setInterval(() => {
      if (popup.closed) {
        clearInterval(checkClosed);
        window.removeEventListener('message', messageHandler);
        reject(new Error('Sign-in was cancelled'));
      }
    }, 1000);
  });
};
