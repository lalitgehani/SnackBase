import '@testing-library/jest-dom'
import { cleanup } from '@testing-library/react'
import { afterAll, afterEach, beforeAll } from 'vitest'
import { SnackBaseClient } from '@snackbase/sdk'
import { setInstanceClientForTests } from '@/lib/snackbase/instanceClientRef'
import { server } from './mocks/server'

// Mock ResizeObserver — jsdom does not implement it, but Radix UI Select uses it
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

// Mock window.scrollTo — jsdom does not implement it
window.scrollTo = () => {}

// Mock pointer capture methods — jsdom does not implement them, but Radix UI Select uses them
Element.prototype.hasPointerCapture = () => false
Element.prototype.setPointerCapture = () => {}
Element.prototype.releasePointerCapture = () => {}

// Mock scrollIntoView — jsdom does not implement it, but Radix UI Select calls it
Element.prototype.scrollIntoView = () => {}

// CodeMirror measures text via Range#getClientRects; jsdom lacks a real layout engine.
const emptyClientRect = () =>
  ({
    x: 0,
    y: 0,
    width: 0,
    height: 0,
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    toJSON() {
      return {}
    },
  }) as DOMRect

if (typeof Range !== 'undefined') {
  Range.prototype.getBoundingClientRect = emptyClientRect
  Range.prototype.getClientRects = () =>
    ({
      length: 0,
      item: () => null,
      [Symbol.iterator]: function* () {},
    }) as DOMRectList
}

Element.prototype.getClientRects = function getClientRects() {
  return {
    length: 1,
    item: () => emptyClientRect(),
    0: emptyClientRect(),
    [Symbol.iterator]: function* () {
      yield emptyClientRect()
    },
  } as unknown as DOMRectList
}

// Start MSW server and mount a test instance client for bindService exports
beforeAll(() => {
  server.listen({ onUnhandledRequest: 'warn' })
  setInstanceClientForTests(
    new SnackBaseClient({
      baseUrl: 'http://localhost',
      storageBackend: 'memory',
      defaultAccount: 'SY0000',
      maxRetries: 0,
    }),
  )
})

// Reset handlers and cleanup DOM after each test
afterEach(async () => {
  cleanup()
  server.resetHandlers()
  try {
    await getInstanceClient().internalAuthManager.clear()
  } catch {
    // Instance client may be unavailable during teardown.
  }
})

// Close MSW server after all tests
afterAll(() => {
  setInstanceClientForTests(null)
  server.close()
})
