import { EditorView } from '@codemirror/view';
import { HighlightStyle, syntaxHighlighting } from '@codemirror/language';
import { tags as t } from '@lezer/highlight';
import type { Extension } from '@codemirror/state';

/**
 * Shared editor chrome styles. Colors come from SnackBase CSS variables so
 * light/dark follow ThemeProvider; `--cm-*` syntax tokens flip in App.css.
 */
const editorChromeStyles = {
  '&': {
    backgroundColor: 'var(--background)',
    color: 'var(--foreground)',
    fontSize: '0.875rem',
    height: '100%',
  },
  '.cm-content': {
    fontFamily:
      'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
    caretColor: 'var(--foreground)',
    paddingTop: '8px',
    paddingBottom: '8px',
  },
  '.cm-cursor, .cm-dropCursor': {
    borderLeftColor: 'var(--foreground)',
  },
  '&.cm-focused .cm-selectionBackground, .cm-selectionBackground, .cm-content ::selection':
    {
      backgroundColor: 'color-mix(in oklch, var(--primary) 22%, transparent)',
    },
  '.cm-activeLine': {
    backgroundColor: 'color-mix(in oklch, var(--muted) 70%, transparent)',
  },
  '.cm-activeLineGutter': {
    backgroundColor: 'color-mix(in oklch, var(--muted) 70%, transparent)',
  },
  '.cm-gutters': {
    backgroundColor: 'var(--muted)',
    color: 'var(--muted-foreground)',
    borderRight: '1px solid var(--border)',
  },
  '.cm-foldPlaceholder': {
    backgroundColor: 'var(--muted)',
    border: 'none',
    color: 'var(--muted-foreground)',
  },
  '.cm-tooltip': {
    backgroundColor: 'var(--popover)',
    color: 'var(--popover-foreground)',
    border: '1px solid var(--border)',
  },
  '.cm-panels': {
    backgroundColor: 'var(--muted)',
    color: 'var(--foreground)',
  },
  '.cm-panels.cm-panels-top': {
    borderBottom: '1px solid var(--border)',
  },
  '.cm-panels.cm-panels-bottom': {
    borderTop: '1px solid var(--border)',
  },
  '.cm-searchMatch': {
    backgroundColor: 'color-mix(in oklch, var(--chart-4) 45%, transparent)',
  },
  '.cm-searchMatch.cm-searchMatch-selected': {
    backgroundColor: 'color-mix(in oklch, var(--chart-1) 45%, transparent)',
  },
  '.cm-scroller': {
    overflow: 'auto',
    fontFamily: 'inherit',
  },
} as const;

const snackbaseEditorThemeLight = EditorView.theme(editorChromeStyles, {
  dark: false,
});

const snackbaseEditorThemeDark = EditorView.theme(editorChromeStyles, {
  dark: true,
});

const snackbaseHighlight = HighlightStyle.define([
  { tag: t.keyword, color: 'var(--cm-keyword)' },
  { tag: t.operator, color: 'var(--cm-operator)' },
  { tag: t.string, color: 'var(--cm-string)' },
  { tag: t.number, color: 'var(--cm-number)' },
  { tag: t.bool, color: 'var(--cm-number)' },
  { tag: t.null, color: 'var(--cm-number)' },
  { tag: t.comment, color: 'var(--muted-foreground)', fontStyle: 'italic' },
  { tag: t.definition(t.variableName), color: 'var(--foreground)' },
  { tag: t.function(t.variableName), color: 'var(--cm-function)' },
  { tag: t.className, color: 'var(--cm-class)' },
  { tag: t.propertyName, color: 'var(--cm-property)' },
  { tag: t.typeName, color: 'var(--cm-type)' },
  { tag: t.bracket, color: 'var(--muted-foreground)' },
  { tag: t.meta, color: 'var(--muted-foreground)' },
  { tag: t.invalid, color: 'var(--destructive)' },
]);

const snackbaseHighlightExtension = syntaxHighlighting(snackbaseHighlight);

/** EditorView theme for the current app appearance (`html.dark`). */
export function snackbaseEditorTheme(dark: boolean): Extension {
  return dark ? snackbaseEditorThemeDark : snackbaseEditorThemeLight;
}

/** Full theme + syntax highlighting. Prefer splitting theme via compartment when dark can flip. */
export function snackbaseEditorExtensions(dark = false): Extension[] {
  return [snackbaseEditorTheme(dark), snackbaseHighlightExtension];
}

export function snackbaseSyntaxHighlighting(): Extension {
  return snackbaseHighlightExtension;
}
