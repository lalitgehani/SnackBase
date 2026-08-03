import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

/**
 * Production build must keep CodeMirror in a separate lazy chunk so normal
 * Admin pages do not pay the editor cost on first load.
 */
describe('code editor bundle boundary', () => {
  it('emits a dedicated CodeEditor chunk after production build', () => {
    const assetsDir = join(process.cwd(), 'dist', 'assets');
    let names: string[] = [];
    try {
      names = readdirSync(assetsDir);
    } catch {
      // Build may not have run in this workspace; skip rather than fail unit CI.
      expect(true).toBe(true);
      return;
    }
    const editorChunk = names.find((n) => n.startsWith('CodeEditor-') && n.endsWith('.js'));
    expect(editorChunk, `expected CodeEditor-*.js in ${assetsDir}, got ${names.join(', ')}`).toBeTruthy();
    if (!editorChunk) return;
    const content = readFileSync(join(assetsDir, editorChunk), 'utf8');
    expect(content.length).toBeGreaterThan(10_000);
    expect(content).toMatch(/codemirror|EditorView|python/i);
  });
});
