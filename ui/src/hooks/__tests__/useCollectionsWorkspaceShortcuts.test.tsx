/**
 * Keyboard shortcut tests for Collections workspace.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {
  COLLECTION_BROWSER_SEARCH_ID,
  SCHEMA_ADD_FIELD_TEST_ID,
  isEditableTarget,
  useCollectionsWorkspaceShortcuts,
} from '@/hooks/useCollectionsWorkspaceShortcuts'

function Harness({ enabled = true }: { enabled?: boolean }) {
  useCollectionsWorkspaceShortcuts({ enabled })
  return (
    <div>
      <input
        id={COLLECTION_BROWSER_SEARCH_ID}
        data-testid={COLLECTION_BROWSER_SEARCH_ID}
        aria-label="Search collections"
      />
      <button type="button" data-testid={SCHEMA_ADD_FIELD_TEST_ID}>
        Add Field
      </button>
      <input data-testid="other-input" aria-label="Other" />
    </div>
  )
}

describe('isEditableTarget', () => {
  it('detects input/textarea/select', () => {
    const input = document.createElement('input')
    const textarea = document.createElement('textarea')
    const select = document.createElement('select')
    const div = document.createElement('div')
    expect(isEditableTarget(input)).toBe(true)
    expect(isEditableTarget(textarea)).toBe(true)
    expect(isEditableTarget(select)).toBe(true)
    expect(isEditableTarget(div)).toBe(false)
  })
})

describe('useCollectionsWorkspaceShortcuts', () => {
  beforeEach(() => {
    document.body.innerHTML = ''
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('focuses browser search on / when not in an input', async () => {
    const user = userEvent.setup()
    render(<Harness />)
    const search = screen.getByTestId(COLLECTION_BROWSER_SEARCH_ID)
    expect(search).not.toHaveFocus()

    await user.keyboard('/')
    expect(search).toHaveFocus()
  })

  it('does not steal focus when / is typed inside an input', async () => {
    const user = userEvent.setup()
    render(<Harness />)
    const other = screen.getByTestId('other-input')
    await user.click(other)
    await user.keyboard('/')
    expect(other).toHaveFocus()
    expect(other).toHaveValue('/')
  })

  it('clicks Add Field on a when button is present', async () => {
    const user = userEvent.setup()
    render(<Harness />)
    const add = screen.getByTestId(SCHEMA_ADD_FIELD_TEST_ID)
    const clickSpy = vi.fn()
    add.addEventListener('click', clickSpy)

    await user.keyboard('a')
    expect(clickSpy).toHaveBeenCalled()
  })

  it('does not trigger add field while typing in an input', async () => {
    const user = userEvent.setup()
    render(<Harness />)
    const other = screen.getByTestId('other-input')
    const add = screen.getByTestId(SCHEMA_ADD_FIELD_TEST_ID)
    const clickSpy = vi.fn()
    add.addEventListener('click', clickSpy)

    await user.click(other)
    await user.keyboard('a')
    expect(clickSpy).not.toHaveBeenCalled()
    expect(other).toHaveValue('a')
  })

  it('ignores shortcuts when disabled', async () => {
    const user = userEvent.setup()
    render(<Harness enabled={false} />)
    const search = screen.getByTestId(COLLECTION_BROWSER_SEARCH_ID)
    await user.keyboard('/')
    expect(search).not.toHaveFocus()
  })
})
