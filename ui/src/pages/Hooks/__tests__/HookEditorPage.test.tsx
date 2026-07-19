import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/utils';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router';
import HookEditorPage from '../editor/HookEditorPage';
import { hooksService } from '@/services/hooks.service';
import { getCollections } from '@/services/collections.service';
import { emailService } from '@/services/email.service';

vi.mock('@/services/hooks.service', () => ({
  hooksService: {
    get: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
  },
}));

vi.mock('@/services/collections.service', () => ({
  getCollections: vi.fn(),
}));

vi.mock('@/services/email.service', () => ({
  emailService: {
    listEmailTemplates: vi.fn(),
  },
}));

const toastMock = vi.fn();
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({ toast: toastMock }),
}));

function renderEditor(path: string) {
  return render(
    <Routes>
      <Route path="/admin/hooks/new" element={<HookEditorPage />} />
      <Route path="/admin/hooks/:id/edit" element={<HookEditorPage />} />
      <Route path="/admin/hooks" element={<div>Hooks list</div>} />
    </Routes>,
    { initialEntries: [path] },
  );
}

describe('HookEditorPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getCollections).mockResolvedValue({
      items: [{ id: 'c1', name: 'posts' } as never],
      total: 1,
      page: 1,
      page_size: 200,
    } as never);
    vi.mocked(emailService.listEmailTemplates).mockResolvedValue([
      {
        id: 'tpl-1',
        account_id: 'x',
        template_type: 'welcome',
        locale: 'en',
        subject: 'Hi',
        html_body: '',
        text_body: '',
        enabled: true,
        is_builtin: true,
        created_at: '',
        updated_at: '',
      },
    ]);
  });

  it('gates create behind template picker; cancel navigates to list', async () => {
    renderEditor('/admin/hooks/new');
    expect(await screen.findByTestId('hook-template-picker')).toBeInTheDocument();
    const user = userEvent.setup();
    await user.click(screen.getByTestId('hook-template-cancel'));
    expect(await screen.findByText('Hooks list')).toBeInTheDocument();
    expect(hooksService.create).not.toHaveBeenCalled();
  });

  it('selecting notify template hydrates event + webhook and shows editor regions', async () => {
    renderEditor('/admin/hooks/new');
    await screen.findByTestId('hook-template-picker');
    const user = userEvent.setup();
    await user.click(screen.getByTestId('hook-template-notify-on-create'));
    expect(await screen.findByTestId('hook-editor-page')).toBeInTheDocument();
    expect(screen.getByTestId('hook-editor-regions')).toBeInTheDocument();
    expect(screen.getByTestId('trigger-config-card')).toBeInTheDocument();
    expect(screen.getByTestId('action-pipeline')).toBeInTheDocument();
    expect(screen.getByTestId('hook-name-input')).toHaveValue('Notify on record create');
  });

  it('blocks save when actions empty (empty template)', async () => {
    renderEditor('/admin/hooks/new');
    await screen.findByTestId('hook-template-picker');
    const user = userEvent.setup();
    await user.click(screen.getByTestId('hook-template-empty'));
    await screen.findByTestId('hook-editor-page');
    await user.clear(screen.getByTestId('hook-name-input'));
    await user.type(screen.getByTestId('hook-name-input'), 'Draft');
    await user.click(screen.getByTestId('hook-editor-save'));
    await waitFor(() => {
      expect(toastMock).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Validation failed',
        }),
      );
    });
    expect(hooksService.create).not.toHaveBeenCalled();
  });

  it('creates multi-action hook and navigates to edit URL', async () => {
    vi.mocked(hooksService.create).mockResolvedValue({
      id: 'new-hk',
      account_id: 'AB1234',
      name: 'Notify on record create',
      description: null,
      trigger: { type: 'event', event: 'records.create' },
      condition: null,
      actions: [{ type: 'send_webhook', url: 'https://example.com/webhook' }],
      enabled: true,
      last_run_at: null,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
      created_by: null,
    });

    renderEditor('/admin/hooks/new');
    await screen.findByTestId('hook-template-picker');
    const user = userEvent.setup();
    await user.click(screen.getByTestId('hook-template-notify-on-create'));
    await screen.findByTestId('hook-editor-page');
    await user.click(screen.getByTestId('hook-editor-save'));

    await waitFor(() => {
      expect(hooksService.create).toHaveBeenCalled();
    });
    const payload = vi.mocked(hooksService.create).mock.calls[0][0];
    expect(payload.trigger).toEqual(
      expect.objectContaining({ type: 'event', event: 'records.create' }),
    );
    expect(payload.actions?.[0]).toMatchObject({
      type: 'send_webhook',
      url: 'https://example.com/webhook',
    });
    // Lands on edit route shell (get will be called for new id)
    await waitFor(() => {
      expect(hooksService.get).toHaveBeenCalledWith('new-hk');
    });
  });

  it('edit save calls update', async () => {
    vi.mocked(hooksService.get).mockResolvedValue({
      id: 'hk-1',
      account_id: 'AB1234',
      name: 'Existing',
      description: null,
      trigger: { type: 'manual' },
      condition: null,
      actions: [{ type: 'send_webhook', url: 'https://x.com', method: 'POST' }],
      enabled: true,
      last_run_at: null,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
      created_by: null,
    });
    vi.mocked(hooksService.update).mockResolvedValue({
      id: 'hk-1',
      account_id: 'AB1234',
      name: 'Existing Renamed',
      description: null,
      trigger: { type: 'manual' },
      condition: null,
      actions: [{ type: 'send_webhook', url: 'https://x.com', method: 'POST' }],
      enabled: true,
      last_run_at: null,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-02T00:00:00Z',
      created_by: null,
    });

    renderEditor('/admin/hooks/hk-1/edit');
    expect(await screen.findByTestId('hook-editor-page')).toBeInTheDocument();
    const user = userEvent.setup();
    const nameInput = screen.getByTestId('hook-name-input');
    await user.clear(nameInput);
    await user.type(nameInput, 'Existing Renamed');
    await user.click(screen.getByTestId('hook-editor-save'));

    await waitFor(() => {
      expect(hooksService.update).toHaveBeenCalledWith(
        'hk-1',
        expect.objectContaining({ name: 'Existing Renamed' }),
      );
    });
  });

  it('shows free-text collection input when collections load fails', async () => {
    vi.mocked(getCollections).mockRejectedValue(new Error('fail'));
    vi.mocked(emailService.listEmailTemplates).mockRejectedValue(new Error('403'));

    renderEditor('/admin/hooks/new');
    await screen.findByTestId('hook-template-picker');
    const user = userEvent.setup();
    await user.click(screen.getByTestId('hook-template-notify-on-create'));
    await screen.findByTestId('hook-editor-page');
    // Editor remains usable
    expect(screen.getByTestId('hook-editor-save')).toBeInTheDocument();
    // Collection filter free-text for record event
    await waitFor(() => {
      expect(screen.getByTestId('trigger-collection-input')).toBeInTheDocument();
    });
  });

  it('shows collection Select when load succeeds', async () => {
    renderEditor('/admin/hooks/new');
    await screen.findByTestId('hook-template-picker');
    const user = userEvent.setup();
    await user.click(screen.getByTestId('hook-template-notify-on-create'));
    await screen.findByTestId('hook-editor-page');
    await waitFor(() => {
      expect(screen.getByTestId('trigger-collection-select')).toBeInTheDocument();
    });
  });

  it('shows error for invalid edit id', async () => {
    vi.mocked(hooksService.get).mockRejectedValue(new Error('404'));
    renderEditor('/admin/hooks/missing/edit');
    expect(await screen.findByTestId('hook-editor-error')).toBeInTheDocument();
    expect(screen.getByText('Back to Hooks')).toBeInTheDocument();
  });
});
