import { describe, expect, it } from 'vitest'

/**
 * Sample test to verify the Vitest setup is working correctly.
 * This file can be deleted once real tests are in place.
 */
describe('Test infrastructure', () => {
  it('runs synchronous tests', () => {
    expect(1 + 1).toBe(2)
  })

  it('runs async tests', async () => {
    const result = await Promise.resolve('vitest is working')
    expect(result).toBe('vitest is working')
  })

  it('supports jest-dom matchers via @testing-library/jest-dom', () => {
    const div = document.createElement('div')
    div.textContent = 'hello'
    document.body.appendChild(div)

    expect(div).toBeInTheDocument()
    expect(div).toHaveTextContent('hello')

    document.body.removeChild(div)
  })
})
