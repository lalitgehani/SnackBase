import { describe, expect, it } from 'vitest';
import { EditorState } from '@codemirror/state';
import { EditorView } from '@codemirror/view';
import {
  snackbaseEditorExtensions,
  snackbaseEditorTheme,
  snackbaseSyntaxHighlighting,
} from '../theme';

describe('code-editor theme', () => {
  it('sets the CodeMirror darkTheme facet for light and dark modes', () => {
    const light = EditorState.create({
      extensions: [snackbaseEditorTheme(false)],
    });
    const dark = EditorState.create({
      extensions: [snackbaseEditorTheme(true)],
    });

    expect(light.facet(EditorView.darkTheme)).toBe(false);
    expect(dark.facet(EditorView.darkTheme)).toBe(true);
  });

  it('wires syntax highlighting through CSS variables', () => {
    const state = EditorState.create({
      doc: 'def handler():\n  return "ok"\n',
      extensions: snackbaseEditorExtensions(true),
    });
    const view = new EditorView({ state });
    try {
      const styleText = [...view.dom.ownerDocument.styleSheets]
        .flatMap((sheet) => {
          try {
            return [...sheet.cssRules].map((rule) => rule.cssText);
          } catch {
            return [];
          }
        })
        .join('\n');
      expect(styleText).toContain('var(--cm-keyword)');
      expect(styleText).toContain('var(--cm-string)');
      expect(styleText).toContain('var(--cm-function)');
      expect(snackbaseSyntaxHighlighting()).toBeTruthy();
    } finally {
      view.destroy();
    }
  });
});
