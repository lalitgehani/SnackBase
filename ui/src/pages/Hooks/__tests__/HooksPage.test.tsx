import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/utils';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router';
import HooksPage from '../HooksPage';
import { hooksService, type Hook } from '@/services/hooks.service';

vi.mock('@/services/hooks.service', () => ({
    hooksService: {
        list: vi.fn(),
        toggle: vi.fn(),
        trigger: vi.fn(),
        delete: vi.fn(),
    },
}));

vi.mock('@/hooks/use-toast', () => ({
    useToast: () => ({ toast: vi.fn() }),
}));

const sampleHook: Hook = {
    id: 'hk-1',
    account_id: 'AB1234',
    name: 'Alpha Hook',
    description: 'Test hook',
    trigger: { type: 'event', event: 'records.create', collection: 'posts' },
    condition: null,
    actions: [{ type: 'send_webhook', url: 'https://example.com' }],
    enabled: true,
    last_run_at: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-02T00:00:00Z',
    created_by: null,
};

function renderList() {
    return render(
        <Routes>
            <Route path="/admin/hooks" element={<HooksPage />} />
            <Route path="/admin/hooks/new" element={<div>New editor</div>} />
            <Route path="/admin/hooks/:id/edit" element={<div>Edit editor</div>} />
            <Route path="/admin/hooks/:id" element={<div>Overview page</div>} />
        </Routes>,
        { initialEntries: ['/admin/hooks'] },
    );
}

describe('HooksPage', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('shows empty state with create CTA navigating to new', async () => {
        vi.mocked(hooksService.list).mockResolvedValue({ items: [], total: 0 });
        renderList();
        expect(await screen.findByTestId('hooks-empty-state')).toBeInTheDocument();
        const user = userEvent.setup();
        await user.click(screen.getByTestId('hooks-empty-create'));
        expect(await screen.findByText('New editor')).toBeInTheDocument();
    });

    it('New Hook button navigates to /hooks/new', async () => {
        vi.mocked(hooksService.list).mockResolvedValue({ items: [], total: 0 });
        renderList();
        await screen.findByTestId('hooks-empty-state');
        const user = userEvent.setup();
        await user.click(screen.getByTestId('hooks-new'));
        expect(await screen.findByText('New editor')).toBeInTheDocument();
    });

    it('navigates to edit on name click and shows trigger badge', async () => {
        vi.mocked(hooksService.list).mockResolvedValue({
            items: [sampleHook],
            total: 1,
        });

        renderList();
        expect(await screen.findByText('Alpha Hook')).toBeInTheDocument();
        expect(screen.getByText('1 action')).toBeInTheDocument();
        expect(screen.getAllByTestId('hook-trigger-badge').length).toBeGreaterThan(0);

        const user = userEvent.setup();
        await user.click(screen.getByTestId('hook-edit-link-hk-1'));
        expect(await screen.findByText('Edit editor')).toBeInTheDocument();
    });

    it('View action navigates to overview route', async () => {
        vi.mocked(hooksService.list).mockResolvedValue({
            items: [sampleHook],
            total: 1,
        });

        renderList();
        expect(await screen.findByText('Alpha Hook')).toBeInTheDocument();

        const user = userEvent.setup();
        await user.click(screen.getByRole('button', { name: /actions/i }));
        await user.click(screen.getByText('View'));
        expect(await screen.findByText('Overview page')).toBeInTheDocument();
    });

    it('Edit menu item navigates to edit route', async () => {
        vi.mocked(hooksService.list).mockResolvedValue({
            items: [sampleHook],
            total: 1,
        });

        renderList();
        await screen.findByText('Alpha Hook');

        const user = userEvent.setup();
        await user.click(screen.getByRole('button', { name: /actions/i }));
        await user.click(screen.getByText('Edit'));
        expect(await screen.findByText('Edit editor')).toBeInTheDocument();
    });

    it('opens delete dialog from menu', async () => {
        vi.mocked(hooksService.list).mockResolvedValue({
            items: [sampleHook],
            total: 1,
        });

        renderList();
        await screen.findByText('Alpha Hook');

        const user = userEvent.setup();
        await user.click(screen.getByRole('button', { name: /actions/i }));
        await user.click(screen.getByText('Delete'));
        expect(await screen.findByText('Delete Hook')).toBeInTheDocument();
        expect(screen.getByText(/Are you sure you want to delete/i)).toBeInTheDocument();
    });

    it('shows enable toggle', async () => {
        vi.mocked(hooksService.list).mockResolvedValue({
            items: [sampleHook],
            total: 1,
        });

        renderList();
        await screen.findByText('Alpha Hook');
        expect(screen.getByTestId('hook-toggle-hk-1')).toBeInTheDocument();
    });

    it('Run Now refreshes list after trigger', async () => {
        vi.mocked(hooksService.list).mockResolvedValue({
            items: [sampleHook],
            total: 1,
        });
        vi.mocked(hooksService.trigger).mockResolvedValue({
            message: 'ok',
            status: 'success',
            actions_executed: 1,
        });

        renderList();
        await screen.findByText('Alpha Hook');

        const user = userEvent.setup();
        await user.click(screen.getByRole('button', { name: /actions/i }));
        await user.click(screen.getByText('Run Now'));

        await waitFor(() => {
            expect(hooksService.trigger).toHaveBeenCalledWith('hk-1');
        });
        await waitFor(() => {
            // list called once on mount + once after trigger
            expect(hooksService.list.mock.calls.length).toBeGreaterThanOrEqual(2);
        });
    });

    it('does not open create/edit/view dialogs from primary actions', async () => {
        vi.mocked(hooksService.list).mockResolvedValue({
            items: [sampleHook],
            total: 1,
        });

        renderList();
        await screen.findByText('Alpha Hook');

        // Dialog titles from legacy create/edit/view should not appear
        expect(screen.queryByText('Create Hook')).not.toBeInTheDocument();
        expect(screen.queryByText('Edit Hook')).not.toBeInTheDocument();
    });
});
