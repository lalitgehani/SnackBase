/**
 * Verifies platform build elimination: self-host dist must not contain the sentinel;
 * platform dist must contain it.
 */
import { describe, it, expect } from 'vitest'
import { execSync } from 'node:child_process'
import { readFileSync, rmSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'

const uiRoot = fileURLToPath(new URL('../..', import.meta.url))
const sentinel = '__SNACKBASE_PLATFORM_BUILD_SENTINEL__'

function distHasSentinel(distDir: string): boolean {
  const walk = (dir: string): boolean => {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const full = join(dir, entry.name)
      if (entry.isDirectory()) {
        if (walk(full)) return true
      } else if (entry.name.endsWith('.js') || entry.name.endsWith('.css')) {
        if (readFileSync(full, 'utf8').includes(sentinel)) return true
      }
    }
    return false
  }
  return walk(distDir)
}

function build(isPlatform: boolean): void {
  const env = isPlatform ? 'VITE_IS_PLATFORM=true' : 'VITE_IS_PLATFORM=false'
  execSync(`${env} npm run build`, { cwd: uiRoot, stdio: 'pipe' })
}

describe('platform build elimination', () => {
  it('excludes platform sentinel from self-host production build', () => {
    build(false)
    expect(distHasSentinel(join(uiRoot, 'dist'))).toBe(false)
  })

  it('includes platform sentinel in platform production build', () => {
    build(true)
    expect(distHasSentinel(join(uiRoot, 'dist'))).toBe(true)
    rmSync(join(uiRoot, 'dist'), { recursive: true, force: true })
    build(false)
  })
})
