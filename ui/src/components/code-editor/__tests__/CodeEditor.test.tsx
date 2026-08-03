import { describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@/test/utils';
import userEvent from '@testing-library/user-event';
import { CodeEditorLazy } from '../index';

describe('CodeEditor', () => {
  it('renders and reports value changes', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <CodeEditorLazy
        path="handler.py"
        value={"print('hi')\n"}
        onChange={onChange}
        height={200}
      />,
    );

    await waitFor(() => {
      expect(screen.getByTestId('code-editor')).toBeInTheDocument();
    });

    const editor = screen.getByTestId('code-editor');
    expect(editor).toHaveAttribute('data-path', 'handler.py');

    // Focus contenteditable and type
    const content = editor.querySelector('.cm-content');
    expect(content).toBeTruthy();
    if (content) {
      await user.click(content);
      await user.keyboard('x');
      await waitFor(() => {
        expect(onChange).toHaveBeenCalled();
      });
    }
  });

  it('honors read-only mode', async () => {
    render(
      <CodeEditorLazy
        path="requirements.txt"
        value="cowsay==6.1\n"
        readOnly
        height={200}
        aria-label="requirements.txt (read-only generated file)"
      />,
    );

    await waitFor(() => {
      expect(screen.getByTestId('code-editor')).toBeInTheDocument();
    });
    const editor = screen.getByTestId('code-editor');
    expect(editor).toHaveAttribute('data-readonly', 'true');
    expect(editor).toHaveAttribute(
      'aria-label',
      'requirements.txt (read-only generated file)',
    );
  });

  it('selects language from path without throwing for unknown types', async () => {
    render(
      <CodeEditorLazy path="notes.txt" value="hello" height={120} />,
    );
    await waitFor(() => {
      expect(screen.getByTestId('code-editor')).toBeInTheDocument();
    });
  });

  it('applies dark theme when the document theme is dark', async () => {
    document.documentElement.classList.add('dark');
    try {
      render(
        <CodeEditorLazy path="handler.py" value="x = 1\n" height={120} />,
      );
      await waitFor(() => {
        expect(screen.getByTestId('code-editor')).toBeInTheDocument();
      });
      await waitFor(() => {
        expect(screen.getByTestId('code-editor')).toHaveAttribute(
          'data-theme',
          'dark',
        );
      });
    } finally {
      document.documentElement.classList.remove('dark');
    }
  });

  it('accepts an injected language extension without Function-page coupling', async () => {
    const marker = [];
    render(
      <CodeEditorLazy
        path="handler.py"
        value="x = 1\n"
        language={{ path: 'handler.py', languageExtension: marker }}
        height={120}
      />,
    );
    await waitFor(() => {
      expect(screen.getByTestId('code-editor')).toBeInTheDocument();
    });
  });
});
