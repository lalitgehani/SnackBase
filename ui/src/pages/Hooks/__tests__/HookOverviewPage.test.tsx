import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/utils';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router';
import HookOverviewPage from '../HookOverviewPage';
import { hooksService } from '@/services/hooks.service';

vi.mock('@/services/hooks.service', () => ({
  hooksService: {
    get: vi.fn(),
    listExecutions: vi.fn(),
    trigger: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

const sampleHook = {
  id: 'hk-1',
  account_id: 'AB1234',
  name: 'Overview Hook',
  description: 'desc',
  trigger: { type: 'event' as const, event: 'records.create', collection: 'posts' },
  condition: 'status == "active"',
  actions: [
    { type: 'send_webhook', url: 'https://hooks.example.com/path' },
    { type: 'send_email', to: 'a@b.com', subject: 'Hi' },
  ],
  enabled: true,
  last_run_at: '2026-01-05T00:00:00Z',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-02T00:00:00Z',
  created_by: null,
};

function renderOverview(path = '/admin/hooks/hk-1') {
  return render(
    <Routes>
      <Route path="/admin/hooks/:id" element={<HookOverviewPage />} />
      <Route path="/admin/hooks" element={<div>Hooks list</div>} />
      <Route path="/admin/hooks/:id/edit" element={<div>Edit page</div>} />
    </Routes>,
    { initialEntries: [path] },
  );
}

describe('HookOverviewPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders config, actions, and executions', async () => {
    vi.mocked(hooksService.get).mockResolvedValue(sampleHook);
    vi.mocked(hooksService.listExecutions).mockResolvedValue({
      items: [
        {
          id: 'ex-1',
          hook_id: 'hk-1',
          trigger_type: 'manual',
          status: 'success',
          actions_executed: 2,
          error_message: null,
          duration_ms: 42,
          executed_at: '2026-01-05T12:00:00Z',
          execution_context: { record: { id: 'r1' } },
        },
      ],
      total: 1,
    });

    renderOverview();
    expect(await screen.findByTestId('hook-overview-page')).toBeInTheDocument();
    expect(screen.getByTestId('overview-name')).toHaveTextContent('Overview Hook');
    expect(screen.getByTestId('overview-config')).toBeInTheDocument();
    expect(screen.getByTestId('overview-action-0')).toBeInTheDocument();
    expect(screen.getByTestId('overview-action-1')).toBeInTheDocument();
    expect(await screen.findByTestId('execution-row-ex-1')).toBeInTheDocument();
    expect(screen.getByText('42ms')).toBeInTheDocument();
  });

  it('expands execution to show context and full error', async () => {
    vi.mocked(hooksService.get).mockResolvedValue(sampleHook);
    vi.mocked(hooksService.listExecutions).mockResolvedValue({
      items: [
        {
          id: 'ex-fail',
          hook_id: 'hk-1',
          trigger_type: 'event',
          status: 'failed',
          actions_executed: 0,
          error_message: 'Full detailed error message here',
          duration_ms: null,
          executed_at: '2026-01-05T12:00:00Z',
          execution_context: { auth: { user_id: 'u1' } },
        },
      ],
      total: 1,
    });

    renderOverview();
    await screen.findByTestId('execution-row-ex-fail');
    const user = userEvent.setup();
    await user.click(screen.getByTestId('execution-row-ex-fail'));
    expect(await screen.findByTestId('execution-expand-ex-fail')).toBeInTheDocument();
    expect(screen.getByTestId('execution-context-ex-fail')).toHaveTextContent('user_id');
    expect(screen.getByTestId('execution-error-ex-fail')).toHaveTextContent(
      'Full detailed error message here',
    );
    expect(screen.getByText('—')).toBeInTheDocument(); // null duration
  });

  it('shows empty context state when absent', async () => {
    vi.mocked(hooksService.get).mockResolvedValue(sampleHook);
    vi.mocked(hooksService.listExecutions).mockResolvedValue({
      items: [
        {
          id: 'ex-2',
          hook_id: 'hk-1',
          trigger_type: 'manual',
          status: 'success',
          actions_executed: 1,
          error_message: null,
          duration_ms: 10,
          executed_at: '2026-01-05T12:00:00Z',
          execution_context: null,
        },
      ],
      total: 1,
    });

    renderOverview();
    await screen.findByTestId('execution-row-ex-2');
    const user = userEvent.setup();
    await user.click(screen.getByTestId('execution-row-ex-2'));
    expect(await screen.findByTestId('execution-context-empty-ex-2')).toHaveTextContent(
      'No context',
    );
  });

  it('Run calls trigger and reloads executions', async () => {
    vi.mocked(hooksService.get).mockResolvedValue(sampleHook);
    vi.mocked(hooksService.listExecutions).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(hooksService.trigger).mockResolvedValue({
      message: 'ok',
      status: 'success',
      actions_executed: 1,
    });

    renderOverview();
    await screen.findByTestId('overview-run');
    const user = userEvent.setup();
    await user.click(screen.getByTestId('overview-run'));

    await waitFor(() => {
      expect(hooksService.trigger).toHaveBeenCalledWith('hk-1');
    });
    await waitFor(() => {
      expect(hooksService.listExecutions.mock.calls.length).toBeGreaterThanOrEqual(2);
      expect(hooksService.get.mock.calls.length).toBeGreaterThanOrEqual(2);
    });
  });

  it('Edit navigates to editor', async () => {
    vi.mocked(hooksService.get).mockResolvedValue(sampleHook);
    vi.mocked(hooksService.listExecutions).mockResolvedValue({ items: [], total: 0 });

    renderOverview();
    await screen.findByTestId('overview-edit');
    const user = userEvent.setup();
    await user.click(screen.getByTestId('overview-edit'));
    expect(await screen.findByText('Edit page')).toBeInTheDocument();
  });

  it('Delete confirms and returns to list', async () => {
    vi.mocked(hooksService.get).mockResolvedValue(sampleHook);
    vi.mocked(hooksService.listExecutions).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(hooksService.delete).mockResolvedValue(undefined);

    renderOverview();
    await screen.findByTestId('overview-delete');
    const user = userEvent.setup();
    await user.click(screen.getByTestId('overview-delete'));
    expect(await screen.findByText('Delete Hook')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /^Delete$/i }));
    await waitFor(() => {
      expect(hooksService.delete).toHaveBeenCalledWith('hk-1');
    });
    expect(await screen.findByText('Hooks list')).toBeInTheDocument();
  });

  it('missing hook shows error + back link', async () => {
    vi.mocked(hooksService.get).mockRejectedValue(new Error('404'));
    vi.mocked(hooksService.listExecutions).mockResolvedValue({ items: [], total: 0 });

    renderOverview('/admin/hooks/missing');
    expect(await screen.findByTestId('hook-overview-error')).toBeInTheDocument();
    expect(screen.getByText('Back to Hooks')).toBeInTheDocument();
  });

  it('shows empty executions message', async () => {
    vi.mocked(hooksService.get).mockResolvedValue(sampleHook);
    vi.mocked(hooksService.listExecutions).mockResolvedValue({ items: [], total: 0 });

    renderOverview();
    expect(await screen.findByTestId('overview-executions-empty')).toBeInTheDocument();
  });
});
