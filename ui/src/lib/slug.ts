/** URL-safe slug pattern (control-plane SCHEMA.md product rule). */
export const SLUG_REGEX = /^[a-z0-9]+(?:-[a-z0-9]+)*$/

export function isValidSlug(value: string): boolean {
  return SLUG_REGEX.test(value)
}

/**
 * Derive a URL-safe slug from a display name.
 * Returns empty string if nothing usable remains.
 */
export function slugifyName(name: string): string {
  return name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .replace(/-{2,}/g, '-')
}
