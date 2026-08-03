import { describe, expect, it } from 'vitest';
import { FUNCTION_TEMPLATES, getTemplate } from '../templates';

describe('function templates', () => {
  it('includes hello, webhook, and openai templates', () => {
    expect(FUNCTION_TEMPLATES.map((t) => t.id)).toEqual(
      expect.arrayContaining(['hello', 'webhook', 'openai']),
    );
  });

  it('hello template defines handler returning JSON shape', () => {
    const hello = getTemplate('hello');
    expect(hello).toBeDefined();
    expect(hello!.files['handler.py']).toContain('def handler');
    expect(hello!.files['handler.py']).toContain('Response.json');
    expect(hello!.auth_required).toBe(true);
  });

  it('openai template includes pinned dependency', () => {
    const openai = getTemplate('openai');
    expect(openai).toBeDefined();
    expect(openai!.dependencies.some((d) => d.startsWith('openai=='))).toBe(true);
  });

  it('webhook template is public', () => {
    expect(getTemplate('webhook')?.auth_required).toBe(false);
  });
});
