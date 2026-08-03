import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/utils';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router';
import FunctionEditorPage from '../FunctionEditorPage';
import { functionsService } from '@/services/functions.service';

vi.mock('@/services/functions.service', () => ({
  functionsService: {
    get: vi.fn(),
    getBody: vi.fn(),
    deploy: vi.fn(),
    test: vi.fn(),
    listExecutions: vi.fn(),
    listVersions: vi.fn(),
    stats: vi.fn(),
    update: vi.fn(),
    updateGrants: vi.fn(),
    activateVersion: vi.fn(),
  },
}));

vi.mock('@/hooks/use-toast', () => {
  const api = { toast: vi.fn() };
  return { useToast: () => api };
});

vi.mock('@/stores/auth.store', () => ({
  useAuthStore: (sel: (s: { account: { slug: string } }) => unknown) =>
    sel({ account: { slug: 'demo' } }),
}));

const baseFn = {
  id: 'fn-1',
  account_id: 'AB1234',
  slug: 'hello',
  name: 'Hello',
  description: null,
  entrypoint: 'handler.py',
  auth_required: true,
  enabled: true,
  status: 'active',
  active_version_id: 'v1',
  grants: { capabilities: [] },
  created_by: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

function renderEditor() {
  return render(
    <Routes>
      <Route path="/admin/functions/:slug" element={<FunctionEditorPage />} />
      <Route path="/admin/functions" element={<div>Functions list</div>} />
    </Routes>,
    { initialEntries: ['/admin/functions/hello'] },
  );
}

describe('FunctionEditorPage multi-file editing', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(functionsService.get).mockResolvedValue(baseFn);
    vi.mocked(functionsService.getBody).mockResolvedValue({
      version_id: 'v1',
      version: 1,
      entrypoint: 'handler.py',
      files: {
        'handler.py': 'def handler(req):\n    return {"ok": True}\n',
        'utils.py': 'def helper():\n    return 1\n',
      },
      dependencies: ['cowsay==6.1'],
      sha256: 'abc',
    });
    vi.mocked(functionsService.listExecutions).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(functionsService.listVersions).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(functionsService.stats).mockResolvedValue({
      total: 0,
      by_status: {},
      p50_ms: null,
      p95_ms: null,
      range: '24h',
    });
  });

  it('loads files and shows CodeMirror instead of a textarea for source', async () => {
    renderEditor();
    expect(await screen.findByRole('heading', { name: 'Hello' })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByTestId('code-editor')).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: /^handler\.py/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^utils\.py/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^requirements\.txt/ })).toBeInTheDocument();
  });

  it('rejects invalid file names inline', async () => {
    const user = userEvent.setup();
    renderEditor();
    await screen.findByRole('heading', { name: 'Hello' });

    const input = screen.getByLabelText('New file name');
    await user.clear(input);
    await user.type(input, '../evil.py');
    await user.click(screen.getByLabelText('Add file'));
    expect(await screen.findByRole('alert')).toHaveTextContent(/\.\./);
  });

  it('creates a nested file path', async () => {
    const user = userEvent.setup();
    renderEditor();
    await screen.findByRole('heading', { name: 'Hello' });

    const input = screen.getByLabelText('New file name');
    await user.type(input, 'lib/formatters.py');
    await user.click(screen.getByLabelText('Add file'));
    expect(await screen.findByRole('button', { name: /^lib\/formatters\.py/ })).toBeInTheDocument();
  });

  it('prevents removing the entrypoint and allows setting another', async () => {
    const user = userEvent.setup();
    renderEditor();
    await screen.findByRole('heading', { name: 'Hello' });

    await user.click(screen.getByRole('button', { name: /^utils\.py/ }));
    const setEp = await screen.findByLabelText('Set utils.py as entrypoint');
    await user.click(setEp);

    // Entrypoint is now utils.py — can remove handler.py
    const removeHandler = screen.getByLabelText('Remove handler.py');
    await user.click(removeHandler);
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /^handler\.py/ })).not.toBeInTheDocument();
    });
  });

  it('deploys files, dependencies, and selected entrypoint', async () => {
    const user = userEvent.setup();
    vi.mocked(functionsService.deploy).mockResolvedValue({
      ...baseFn,
      active_version_id: 'v2',
    } as never);

    renderEditor();
    await screen.findByRole('heading', { name: 'Hello' });
    await waitFor(() => expect(screen.getByTestId('code-editor')).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /^utils\.py/ }));
    await user.click(await screen.findByLabelText('Set utils.py as entrypoint'));
    await user.click(screen.getByLabelText('Deploy function'));

    await waitFor(() => {
      expect(functionsService.deploy).toHaveBeenCalled();
    });
    const payload = vi.mocked(functionsService.deploy).mock.calls[0][1];
    expect(payload.entrypoint).toBe('utils.py');
    expect(payload.dependencies).toEqual(['cowsay==6.1']);
    expect(payload.files['requirements.txt']).toBe('cowsay==6.1\n');
    expect(payload.files['handler.py']).toContain('handler');
    expect(payload.files['utils.py']).toContain('helper');
  });

  it('marks requirements.txt read-only', async () => {
    const user = userEvent.setup();
    renderEditor();
    await screen.findByRole('heading', { name: 'Hello' });
    await user.click(screen.getByRole('button', { name: /^requirements\.txt/ }));
    await waitFor(() => {
      expect(screen.getByTestId('code-editor')).toHaveAttribute('data-readonly', 'true');
    });
    expect(screen.getByText(/Generated from the Dependencies panel/i)).toBeInTheDocument();
  });

  it('shows unsaved changes after editing and clears after successful deploy', async () => {
    const user = userEvent.setup();
    vi.mocked(functionsService.deploy).mockResolvedValue({
      ...baseFn,
      active_version_id: 'v2',
    } as never);
    vi.mocked(functionsService.getBody).mockImplementation(async () => ({
      version_id: 'v2',
      version: 2,
      entrypoint: 'utils.py',
      files: {
        'handler.py': 'def handler(req):\n    return {"ok": True}\n',
        'utils.py': 'def helper():\n    return 1\n',
      },
      dependencies: ['cowsay==6.1'],
      sha256: 'def',
    }));
    // First load uses the beforeEach mock; re-mock after render for post-deploy reload
    vi.mocked(functionsService.getBody).mockResolvedValueOnce({
      version_id: 'v1',
      version: 1,
      entrypoint: 'handler.py',
      files: {
        'handler.py': 'def handler(req):\n    return {"ok": True}\n',
        'utils.py': 'def helper():\n    return 1\n',
      },
      dependencies: ['cowsay==6.1'],
      sha256: 'abc',
    });

    renderEditor();
    await screen.findByRole('heading', { name: 'Hello' });
    await waitFor(() => expect(screen.getByTestId('code-editor')).toBeInTheDocument());
    expect(screen.queryByTestId('unsaved-changes')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /^utils\.py/ }));
    await user.click(await screen.findByLabelText('Set utils.py as entrypoint'));
    expect(await screen.findByTestId('unsaved-changes')).toBeInTheDocument();

    // Subsequent getBody calls after deploy return the new baseline
    vi.mocked(functionsService.getBody).mockResolvedValue({
      version_id: 'v2',
      version: 2,
      entrypoint: 'utils.py',
      files: {
        'handler.py': 'def handler(req):\n    return {"ok": True}\n',
        'utils.py': 'def helper():\n    return 1\n',
      },
      dependencies: ['cowsay==6.1'],
      sha256: 'def',
    });

    await user.click(screen.getByLabelText('Deploy function'));
    await waitFor(() => {
      expect(functionsService.deploy).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(screen.queryByTestId('unsaved-changes')).not.toBeInTheDocument();
    });
  });

  it('keeps dirty state when deploy fails', async () => {
    const user = userEvent.setup();
    vi.mocked(functionsService.deploy).mockRejectedValue({
      response: { data: { detail: 'boom' } },
    });

    renderEditor();
    await screen.findByRole('heading', { name: 'Hello' });
    await user.click(screen.getByRole('button', { name: /^utils\.py/ }));
    await user.click(await screen.findByLabelText('Set utils.py as entrypoint'));
    expect(await screen.findByTestId('unsaved-changes')).toBeInTheDocument();

    await user.click(screen.getByLabelText('Deploy function'));
    await waitFor(() => {
      expect(screen.getByText(/Deploy error/i)).toBeInTheDocument();
    });
    expect(screen.getByTestId('unsaved-changes')).toBeInTheDocument();
  });
});

describe('FunctionEditorPage version compare', () => {
  const versions = [
    {
      id: 'ver-1',
      function_id: 'fn-1',
      version: 1,
      dependencies: ['cowsay==6.0'],
      sha256: 'aaaaaaaaaaaa1111',
      env_path: null,
      created_by: null,
      created_at: '2026-01-01T00:00:00Z',
    },
    {
      id: 'ver-2',
      function_id: 'fn-1',
      version: 2,
      dependencies: ['cowsay==6.1'],
      sha256: 'bbbbbbbbbbbb2222',
      env_path: null,
      created_by: null,
      created_at: '2026-01-02T00:00:00Z',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(functionsService.get).mockResolvedValue(baseFn);
    vi.mocked(functionsService.getBody).mockResolvedValue({
      version_id: 'ver-2',
      version: 2,
      entrypoint: 'handler.py',
      files: {
        'handler.py': 'print("v2")\n',
      },
      dependencies: ['cowsay==6.1'],
      sha256: 'bbbbbbbbbbbb2222',
    });
    vi.mocked(functionsService.listExecutions).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(functionsService.listVersions).mockResolvedValue({
      items: versions,
      total: 2,
    });
    vi.mocked(functionsService.stats).mockResolvedValue({
      total: 0,
      by_status: {},
      p50_ms: null,
      p95_ms: null,
      range: '24h',
    });
  });

  it('keeps Compare disabled until two versions are selected', async () => {
    const user = userEvent.setup();
    renderEditor();
    await screen.findByRole('heading', { name: 'Hello' });
    await user.click(screen.getByRole('tab', { name: 'Versions' }));

    const compareBtn = await screen.findByRole('button', {
      name: 'Compare selected versions',
    });
    expect(compareBtn).toBeDisabled();

    await user.click(screen.getByLabelText('Select version 1 for compare'));
    expect(compareBtn).toBeDisabled();

    await user.click(screen.getByLabelText('Select version 2 for compare'));
    expect(compareBtn).toBeEnabled();
    expect(screen.getByText('v1 vs v2')).toBeInTheDocument();
  });

  it('loads both bodies and opens the compare sheet', async () => {
    const user = userEvent.setup();
    vi.mocked(functionsService.getBody).mockImplementation(async (_slug, versionId) => {
      if (versionId === 'ver-1') {
        return {
          version_id: 'ver-1',
          version: 1,
          entrypoint: 'handler.py',
          files: { 'handler.py': 'print("v1")\n' },
          dependencies: ['cowsay==6.0'],
          sha256: 'aaaaaaaaaaaa1111',
        };
      }
      return {
        version_id: 'ver-2',
        version: 2,
        entrypoint: 'handler.py',
        files: { 'handler.py': 'print("v2")\n' },
        dependencies: ['cowsay==6.1'],
        sha256: 'bbbbbbbbbbbb2222',
      };
    });

    renderEditor();
    await screen.findByRole('heading', { name: 'Hello' });
    await user.click(screen.getByRole('tab', { name: 'Versions' }));
    await user.click(screen.getByLabelText('Select version 1 for compare'));
    await user.click(screen.getByLabelText('Select version 2 for compare'));
    await user.click(screen.getByRole('button', { name: 'Compare selected versions' }));

    await waitFor(() => {
      expect(functionsService.getBody).toHaveBeenCalledWith('hello', 'ver-1');
      expect(functionsService.getBody).toHaveBeenCalledWith('hello', 'ver-2');
    });
    expect(await screen.findByTestId('version-compare-sheet')).toBeInTheDocument();
    expect(screen.getByTestId('version-compare-diff')).toBeInTheDocument();
  });
});
