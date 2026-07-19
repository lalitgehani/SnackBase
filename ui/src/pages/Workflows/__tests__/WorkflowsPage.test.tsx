import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@/test/utils';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router';
import WorkflowsPage from '../WorkflowsPage';
import { workflowsService } from '@/services/workflows.service';

vi.mock('@/services/workflows.service', () => ({
    workflowsService: {
        list: vi.fn(),
        toggle: vi.fn(),
        trigger: vi.fn(),
    },
}));

vi.mock('@/hooks/use-toast', () => ({
    useToast: () => ({ toast: vi.fn() }),
}));

function renderList() {
    return render(
        <Routes>
            <Route path="/admin/workflows" element={<WorkflowsPage />} />
            <Route path="/admin/workflows/new" element={<div>New editor</div>} />
            <Route path="/admin/workflows/:id/edit" element={<div>Edit editor</div>} />
            <Route path="/admin/workflows/:id" element={<div>Overview page</div>} />
        </Routes>,
        { initialEntries: ['/admin/workflows'] },
    );
}

describe('WorkflowsPage', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('shows empty state with create CTA', async () => {
        vi.mocked(workflowsService.list).mockResolvedValue({ items: [], total: 0 });
        renderList();
        expect(await screen.findByTestId('workflows-empty-state')).toBeInTheDocument();
        const user = userEvent.setup();
        await user.click(screen.getByTestId('workflows-empty-create'));
        expect(await screen.findByText('New editor')).toBeInTheDocument();
    });

    it('shows step count and navigates to edit on name click', async () => {
        vi.mocked(workflowsService.list).mockResolvedValue({
            items: [
                {
                    id: 'wf-1',
                    account_id: 'AB1234',
                    name: 'Alpha',
                    description: null,
                    trigger_type: 'manual',
                    trigger_config: { type: 'manual' },
                    steps: [
                        { type: 'action', name: 'a' },
                        { type: 'action', name: 'b' },
                    ],
                    enabled: true,
                    created_at: '2026-01-01T00:00:00Z',
                    updated_at: '2026-01-02T00:00:00Z',
                    created_by: null,
                },
            ],
            total: 1,
        });

        renderList();
        expect(await screen.findByText('2 steps')).toBeInTheDocument();
        expect(screen.getByText('Updated')).toBeInTheDocument();

        const user = userEvent.setup();
        await user.click(screen.getByTestId('workflow-edit-link-wf-1'));
        expect(await screen.findByText('Edit editor')).toBeInTheDocument();
    });

    it('View action navigates to overview route', async () => {
        vi.mocked(workflowsService.list).mockResolvedValue({
            items: [
                {
                    id: 'wf-1',
                    account_id: 'AB1234',
                    name: 'Alpha',
                    description: null,
                    trigger_type: 'manual',
                    trigger_config: { type: 'manual' },
                    steps: [{ type: 'action', name: 'a' }],
                    enabled: true,
                    created_at: '2026-01-01T00:00:00Z',
                    updated_at: '2026-01-02T00:00:00Z',
                    created_by: null,
                },
            ],
            total: 1,
        });

        renderList();
        expect(await screen.findByText('Alpha')).toBeInTheDocument();

        const user = userEvent.setup();
        await user.click(screen.getByRole('button', { name: /actions/i }));
        await user.click(screen.getByText('View'));
        expect(await screen.findByText('Overview page')).toBeInTheDocument();
    });
});
