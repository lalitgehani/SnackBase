/**
 * Structural guard: Playwright resolves fixtures by the property name in the
 * test callback's destructuring object. Renaming the binding with a leading
 * underscore alone (e.g. `_authenticatedPage`) breaks fixture injection.
 * Allowed: `authenticatedPage` or `authenticatedPage: _auth`.
 */
import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const uiRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const fixturesPath = path.join(uiRoot, 'e2e/fixtures.ts')
const testsDir = path.join(uiRoot, 'e2e/tests')

function collectTsFiles(dir: string): string[] {
  const out: string[] = []
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) out.push(...collectTsFiles(full))
    else if (entry.name.endsWith('.ts') || entry.name.endsWith('.tsx')) out.push(full)
  }
  return out
}

function fixtureNamesFromFixturesFile(source: string): Set<string> {
  // Match keys in PageFixtures type or base.extend object, e.g. `authenticatedPage:`
  const names = new Set<string>()
  const re = /^\s{2}([a-zA-Z_][a-zA-Z0-9_]*)\s*:/gm
  let m: RegExpExecArray | null
  while ((m = re.exec(source)) !== null) {
    const name = m[1]
    // Skip type-only noise
    if (name === 'type' || name === 'export') continue
    names.add(name)
  }
  return names
}

describe('e2e Playwright fixture parameter names', () => {
  it('defines authenticatedPage fixture under its real name', () => {
    const source = fs.readFileSync(fixturesPath, 'utf8')
    expect(source).toMatch(/authenticatedPage\s*:/)
    expect(source).not.toMatch(/_authenticatedPage\s*:/)
  })

  it('tests request fixtures by real name (not underscore-prefixed fixture keys)', () => {
    const fixturesSource = fs.readFileSync(fixturesPath, 'utf8')
    const known = fixtureNamesFromFixturesFile(fixturesSource)
    // Always check the high-value auth fixture even if regex is incomplete
    known.add('authenticatedPage')

    const testFiles = collectTsFiles(testsDir)
    expect(testFiles.length).toBeGreaterThan(0)

    const bad: string[] = []
    for (const file of testFiles) {
      const text = fs.readFileSync(file, 'utf8')
      for (const name of known) {
        // Ban bare `_name` as a destructured fixture key (Playwright won't inject it)
        const bareUnderscore = new RegExp(`\\b_${name}\\b`)
        if (bareUnderscore.test(text)) {
          bad.push(`${path.relative(uiRoot, file)}: uses _${name} as fixture key (use \`${name}: _alias\` instead)`)
        }
      }
    }

    expect(bad, bad.join('\n')).toEqual([])
  })

  it('uses authenticatedPage via real name or rename form in suites that need auth', () => {
    const suites = [
      'e2e/tests/auth.test.ts',
      'e2e/tests/collections.test.ts',
      'e2e/tests/navigation.test.ts',
      'e2e/tests/user-management.test.ts',
    ]
    for (const rel of suites) {
      const text = fs.readFileSync(path.join(uiRoot, rel), 'utf8')
      expect(text, rel).toMatch(/authenticatedPage(?:\s*:)?/)
      expect(text, rel).not.toMatch(/\b_authenticatedPage\b/)
    }
  })
})
