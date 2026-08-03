import { describe, expect, it } from 'vitest';
import {
  generateRequirementsTxt,
  isPinnedDependency,
  isRequirementsFile,
  normalizeDependencies,
  validateSourcePath,
} from '../functionSourceUtils';

describe('validateSourcePath', () => {
  const existing = { 'handler.py': 'x' };

  it('accepts nested relative paths', () => {
    expect(validateSourcePath('lib/formatters.py', existing)).toBeNull();
  });

  it('rejects empty, duplicate, absolute, traversal, backslash, and overlong names', () => {
    expect(validateSourcePath('', existing)).toMatch(/required/i);
    expect(validateSourcePath('handler.py', existing)).toMatch(/already exists/i);
    expect(validateSourcePath('/abs.py', existing)).toMatch(/Absolute/i);
    expect(validateSourcePath('../outside.py', existing)).toMatch(/\.\./);
    expect(validateSourcePath('lib/../../outside.py', existing)).toMatch(/\.\./);
    expect(validateSourcePath('lib\\evil.py', existing)).toMatch(/Backslash/i);
    expect(validateSourcePath('a'.repeat(256), existing)).toMatch(/255/);
  });
});

describe('dependency helpers', () => {
  it('validates exact pins', () => {
    expect(isPinnedDependency('cowsay==6.1')).toBe(true);
    expect(isPinnedDependency('cowsay')).toBe(false);
    expect(isPinnedDependency('cowsay>=6')).toBe(false);
  });

  it('normalizes whitespace and duplicates', () => {
    expect(normalizeDependencies([' cowsay == 6.1 ', 'httpx==0.28.0', 'cowsay==6.0'])).toEqual([
      'cowsay==6.0',
      'httpx==0.28.0',
    ]);
  });

  it('generates requirements.txt including empty content', () => {
    expect(generateRequirementsTxt([])).toBe('');
    expect(generateRequirementsTxt(['cowsay==6.1'])).toBe('cowsay==6.1\n');
  });

  it('detects requirements.txt', () => {
    expect(isRequirementsFile('requirements.txt')).toBe(true);
    expect(isRequirementsFile('handler.py')).toBe(false);
  });
});
