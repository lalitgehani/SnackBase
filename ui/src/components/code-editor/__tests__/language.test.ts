import { describe, expect, it } from 'vitest';
import { languageExtensionFor, resolveLanguageId } from '../language';
import type { EditorLanguageContext } from '../types';

describe('resolveLanguageId', () => {
  it('maps .py and .pyi to python', () => {
    expect(resolveLanguageId('handler.py')).toBe('python');
    expect(resolveLanguageId('lib/types.pyi')).toBe('python');
  });

  it('maps .json to json', () => {
    expect(resolveLanguageId('config.json')).toBe('json');
  });

  it('maps .sql to sql id without installing a package', () => {
    expect(resolveLanguageId('query.sql')).toBe('sql');
  });

  it('maps unknown extensions to plaintext', () => {
    expect(resolveLanguageId('README.md')).toBe('plaintext');
    expect(resolveLanguageId('Makefile')).toBe('plaintext');
    expect(resolveLanguageId(undefined)).toBe('plaintext');
  });
});

describe('languageExtensionFor', () => {
  it('selects language through the adapter boundary', () => {
    expect(languageExtensionFor({ path: 'a.py' })).toBeTruthy();
    expect(languageExtensionFor({ path: 'a.json' })).toBeTruthy();
    expect(languageExtensionFor({ path: 'a.txt' })).toEqual([]);
    expect(languageExtensionFor({ path: 'a.sql' })).toEqual([]);
  });

  it('accepts an injected test-only language extension', () => {
    const marker = { __testLang: true };
    const ctx: EditorLanguageContext = {
      path: 'x.py',
      languageExtension: marker,
    };
    expect(languageExtensionFor(ctx)).toBe(marker);
  });

  it('documents dialect and schema slots for future SQL without requiring them', () => {
    const futureSql: EditorLanguageContext = {
      path: 'analytics.sql',
      languageId: 'sql',
      dialect: 'postgresql',
      schema: [{ label: 'todos', columns: [{ label: 'id', type: 'text' }] }],
    };
    // No SQL package installed; falls back to plaintext extension list.
    expect(languageExtensionFor(futureSql)).toEqual([]);
    expect(futureSql.dialect).toBe('postgresql');
    expect(futureSql.schema?.[0]?.label).toBe('todos');
  });
});
