import { expectTypeOf } from 'vitest'
import type { RuntimeSnackbaseEnv } from '../config'

describe('RuntimeSnackbaseEnv type', () => {
  it('declares exactly the four URL fields', () => {
    expectTypeOf<RuntimeSnackbaseEnv>().toMatchTypeOf<{
      apiBaseUrl?: string
      platformPathPrefix?: string
      snackbaseUrl?: string
      provisionApiUrl?: string
    }>()
  })

  it('rejects isPlatform member at compile time', () => {
    // @ts-expect-error isPlatform is not a member of RuntimeSnackbaseEnv
    const bad: RuntimeSnackbaseEnv = { isPlatform: true }
    expect(bad).toBeDefined()
  })
})
