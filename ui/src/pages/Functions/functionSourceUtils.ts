/**
 * Shared Function source-path rules used by the Admin editor.
 * Backend deploy validation mirrors these checks.
 */

export const REQUIREMENTS_FILE = 'requirements.txt';
export const MAX_SOURCE_PATH_LENGTH = 255;

export function validateSourcePath(
  name: string,
  existing: Record<string, string>,
): string | null {
  const trimmed = name.trim();
  if (!trimmed) return 'File name is required';
  if (trimmed.length > MAX_SOURCE_PATH_LENGTH) {
    return `File name must be at most ${MAX_SOURCE_PATH_LENGTH} characters`;
  }
  if (trimmed.startsWith('/')) return 'Absolute paths are not allowed';
  if (trimmed.includes('\\')) return 'Backslashes are not allowed';
  if (trimmed.includes('\0')) return 'File name contains invalid characters';
  if (trimmed.split('/').some((part) => part === '..' || part === '')) {
    return 'Path must be a relative POSIX path without ".." segments';
  }
  if (Object.prototype.hasOwnProperty.call(existing, trimmed)) {
    return 'A file with this name already exists';
  }
  return null;
}

export function isRequirementsFile(path: string): boolean {
  return path === REQUIREMENTS_FILE || path.endsWith(`/${REQUIREMENTS_FILE}`);
}

/** Exact pin form accepted by the Functions deploy API. */
export function isPinnedDependency(dep: string): boolean {
  return /^[A-Za-z0-9][A-Za-z0-9._-]*\s*==\s*[A-Za-z0-9][A-Za-z0-9._+!-]*$/.test(
    dep.trim(),
  );
}

/**
 * Normalize dependency pins: trim, drop empties, dedupe by package name
 * (last pin wins), preserve order of first occurrence of each package key.
 */
export function normalizeDependencies(deps: string[]): string[] {
  const byPackage = new Map<string, string>();
  const order: string[] = [];
  for (const raw of deps) {
    const pin = raw.trim();
    if (!pin) continue;
    const pkg = pin.split('==')[0]?.trim().toLowerCase() ?? pin.toLowerCase();
    if (!byPackage.has(pkg)) order.push(pkg);
    byPackage.set(pkg, pin.replace(/\s+/g, ''));
  }
  return order.map((pkg) => byPackage.get(pkg)!);
}

/** Generate requirements.txt content from normalized pins (empty file when none). */
export function generateRequirementsTxt(deps: string[]): string {
  const pins = normalizeDependencies(deps);
  if (pins.length === 0) return '';
  return pins.join('\n') + '\n';
}
