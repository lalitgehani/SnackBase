/**
 * Resolve a provider logo path returned by the API into a URL the browser can
 * load.
 *
 * Provider definitions return root-absolute paths such as
 * `/assets/providers/system.svg`, but the admin UI is served from
 * `import.meta.env.BASE_URL` (`/_/` in production builds, `/` under the Vite
 * dev server). A root-absolute path is requested from the site root, where the
 * asset does not exist, so it must be prefixed with the app base.
 */
export function resolveProviderLogoUrl(
    logoUrl?: string | null,
    baseUrl: string = import.meta.env.BASE_URL,
): string | undefined {
    if (!logoUrl) {
        return undefined;
    }

    // External absolute URLs, data URLs, and protocol-relative URLs are already
    // loadable as-is.
    if (!logoUrl.startsWith('/') || logoUrl.startsWith('//')) {
        return logoUrl;
    }

    const base = baseUrl.endsWith('/') ? baseUrl : `${baseUrl}/`;

    if (base === '/') {
        return logoUrl;
    }

    // Leave paths that already carry the base prefix untouched.
    if (logoUrl.startsWith(base)) {
        return logoUrl;
    }

    return `${base}${logoUrl.slice(1)}`;
}
