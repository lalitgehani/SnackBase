import '@testing-library/jest-dom'
import { cleanup } from '@testing-library/react'
import { afterAll, afterEach, beforeAll } from 'vitest'
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

// Start MSW server before all tests
beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }))

// Reset handlers and cleanup DOM after each test
afterEach(() => {
  cleanup()
  server.resetHandlers()
})

// Close MSW server after all tests
afterAll(() => server.close())
