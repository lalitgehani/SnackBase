/** SDK localStorage key for instance auth tokens (self-host mode). */
export const AUTH_STORAGE_KEY = 'snackbase-auth';

/**
 * SDK localStorage key for the control-plane session (platform mode).
 *
 * The control-plane client is constructed without `authStorageKey`
 * (`src/lib/control-plane/client.ts`), so the SDK's AuthManager falls back to its own
 * default. Kept here so the session bridge can read the persisted token synchronously.
 */
export const CONTROL_PLANE_AUTH_STORAGE_KEY = 'sb_auth_state';
