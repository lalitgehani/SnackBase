/**
 * Error helpers for Studio (instance) and platform (control-plane) surfaces.
 */

/** Normalize SDK / network errors into a user-facing string. */
export function getErrorMessage(err: unknown, fallback = 'Something went wrong'): string {
  if (err && typeof err === 'object') {
    const obj = err as Record<string, unknown>;
    const details = obj.details;
    if (details && typeof details === 'object') {
      const d = details as Record<string, unknown>;
      if (typeof d.detail === 'string' && d.detail) {
        return d.detail;
      }
      if (typeof d.message === 'string' && d.message) {
        return d.message;
      }
    }
    if (typeof details === 'string' && details.trim()) {
      return details;
    }
  }

  let raw = '';
  if (err instanceof Error && err.message) {
    raw = err.message;
  } else if (typeof err === 'string' && err.trim()) {
    raw = err;
  } else if (err && typeof err === 'object') {
    const obj = err as Record<string, unknown>;
    if (typeof obj.message === 'string' && obj.message) {
      raw = obj.message;
    } else if (typeof obj.detail === 'string' && obj.detail) {
      raw = obj.detail;
    } else if (obj.detail && typeof obj.detail === 'object') {
      const d = obj.detail as Record<string, unknown>;
      if (typeof d.message === 'string') raw = d.message;
    }
  }

  if (!raw) return fallback;

  const lower = raw.toLowerCase();
  if (
    lower.includes('does not satisfy collection rules') ||
    lower.includes('satisfy collection rules')
  ) {
    return (
      'This change is not allowed (invalid region, tenancy mode, or status). ' +
      'Choose an available region and single/multi tenancy.'
    );
  }
  if (
    lower.includes('field access denied') ||
    lower.includes('permission denied to') ||
    lower.includes('unauthorized_fields')
  ) {
    return 'You cannot change this field. Provisioning fields are managed by the platform.';
  }

  return raw;
}

/** Instance Studio API error helper (alias used across admin pages). */
export function handleApiError(error: unknown): string {
  return getErrorMessage(error, 'An unexpected error occurred');
}
