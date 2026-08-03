import type { Extension } from '@codemirror/state';
import { python } from '@codemirror/lang-python';
import { json } from '@codemirror/lang-json';
import type { EditorLanguageContext, EditorLanguageId } from './types';

/**
 * Resolve a language ID from a file path extension.
 * Unknown extensions map to plaintext (no language package).
 */
export function resolveLanguageId(path: string | undefined): EditorLanguageId {
  if (!path) return 'plaintext';
  const base = path.split('/').pop() ?? path;
  const lower = base.toLowerCase();
  if (lower.endsWith('.py') || lower.endsWith('.pyi')) return 'python';
  if (lower.endsWith('.json')) return 'json';
  if (lower.endsWith('.sql')) return 'sql';
  return 'plaintext';
}

/**
 * Build the CodeMirror language extension for a context.
 * SQL is intentionally not installed here; callers may supply
 * `languageExtension` (e.g. from `@codemirror/lang-sql`) without
 * changing this module or Function-page deploy code.
 */
export function languageExtensionFor(
  context: EditorLanguageContext | undefined,
): Extension {
  if (context?.languageExtension != null) {
    return context.languageExtension as Extension;
  }
  const id = context?.languageId ?? resolveLanguageId(context?.path);
  switch (id) {
    case 'python':
      return python();
    case 'json':
      return json();
    case 'sql':
      // SQL package is not installed in this phase. Plaintext until a SQL Editor
      // supplies languageExtension / dialect / schema via EditorLanguageContext.
      return [];
    default:
      return [];
  }
}
