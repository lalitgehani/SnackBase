/**
 * Shared language context for the SnackBase code editor.
 *
 * Language resolution is extension-based. Future SQL editors can register
 * `@codemirror/lang-sql` with dialect + schema metadata without changing
 * file-state, dirty tracking, or editor chrome.
 *
 * SQL extension checklist (not implemented in this product):
 * 1. Install `@codemirror/lang-sql`.
 * 2. Pass `languageExtension` from `sql({ dialect, schema })`.
 * 3. Set `dialect` from the instance DB backend (sqlite / postgresql).
 * 4. Populate `schema` from SnackBase collection metadata.
 * 5. Keep query execution, results, history, and permissions as a separate feature.
 */
export type EditorLanguageId = 'python' | 'json' | 'plaintext' | 'sql' | (string & {});

/**
 * Optional SQL dialect identifiers for a future SQL Editor.
 * Not used by the Functions page.
 */
export type SqlDialectId =
  | 'sqlite'
  | 'postgresql'
  | 'mysql'
  | 'mssql'
  | 'standard'
  | (string & {});

/**
 * Optional schema completion metadata for a future SQL Editor.
 * Functions never supply this; the SQL product would populate it from
 * SnackBase collection metadata.
 */
export interface SqlSchemaTable {
  label: string;
  detail?: string;
  columns?: Array<{ label: string; detail?: string; type?: string }>;
}

export interface EditorLanguageContext {
  /** Absolute or relative path used for language resolution and a11y labels. */
  path?: string;
  /** Explicit language override; when omitted, resolved from `path`. */
  languageId?: EditorLanguageId;
  /**
   * Future SQL dialect (e.g. sqlite / postgresql). Ignored for non-SQL languages.
   * Reserved for `@codemirror/lang-sql` integration.
   */
  dialect?: SqlDialectId;
  /**
   * Future schema completion data (tables/columns). Ignored for non-SQL languages.
   * Reserved for `@codemirror/lang-sql` schema completion.
   */
  schema?: SqlSchemaTable[];
  /**
   * Escape hatch for test-only or future language extensions.
   * When provided, replaces the built-in language package for this document.
   */
  languageExtension?: unknown;
}

export interface CodeEditorProps {
  /** Active document path (drives language resolution and per-file state keys). */
  path: string;
  /** Current document text. */
  value: string;
  /** Fired when the user edits the document. */
  onChange?: (value: string) => void;
  /** Language context; see {@link EditorLanguageContext}. */
  language?: EditorLanguageContext;
  /** When true, editing is disabled (e.g. generated requirements.txt). */
  readOnly?: boolean;
  /** CSS height (default 420px). */
  height?: string | number;
  /** Optional className for the outer container. */
  className?: string;
  /** Autofocus the editor on mount. */
  autoFocus?: boolean;
  /** Accessible name for the editor surface. */
  'aria-label'?: string;
  /**
   * Open file paths. Cached EditorState entries for paths not in this list
   * are discarded so removing a tab does not retain editor resources.
   */
  openPaths?: string[];
}
