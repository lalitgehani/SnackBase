import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/utils';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router';
import WorkflowEditorPage from '../WorkflowEditorPage';
import { workflowsService } from '@/services/workflows.service';

vi.mock('@/services/workflows.service', () => ({
    workflowsService: {
        get: vi.fn(),
        create: vi.fn(),
        update: vi.fn(),
    },
}));

vi.mock('@/hooks/use-toast', () => ({
    useToast: () => ({ toast: vi.fn() }),
}));

// React Flow ResizeObserver in jsdom
class ResizeObserverMock {
    observe() {}
    unobserve() {}
    disconnect() {}
}
vi.stubGlobal('ResizeObserver', ResizeObserverMock);

function renderEditor(path: string) {
    return render(
        <Routes>
            <Route path="/admin/workflows/new" element={<WorkflowEditorPage />} />
            <Route path="/admin/workflows/:id/edit" element={<WorkflowEditorPage />} />
            <Route path="/admin/workflows" element={<div>Workflows List</div>} />
        </Routes>,
        { initialEntries: [path] },
    );
}

describe('WorkflowEditorPage', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders new workflow editor shell', async () => {
        renderEditor('/admin/workflows/new');

        expect(await screen.findByTestId('workflow-editor-page')).toBeInTheDocument();
        expect(screen.getByTestId('workflow-editor-name')).toBeInTheDocument();
        expect(screen.getByTestId('workflow-editor-save')).toBeInTheDocument();
        expect(screen.getByTestId('workflow-editor-palette')).toBeInTheDocument();
        expect(screen.getByTestId('workflow-editor-properties')).toBeInTheDocument();
        expect(screen.getByTestId('workflow-canvas')).toBeInTheDocument();
    });

    it('loads existing workflow on edit route', async () => {
        vi.mocked(workflowsService.get).mockResolvedValue({
            id: 'wf-1',
            account_id: 'AB1234',
            name: 'My Flow',
            description: 'desc',
            trigger_type: 'manual',
            trigger_config: { type: 'manual' },
            steps: [
                {
                    type: 'action',
                    name: 'notify',
                    action_type: 'send_webhook',
                    config: { url: 'https://x.com' },
                    position_x: 40,
                    position_y: 80,
                },
            ],
            enabled: true,
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
            created_by: null,
        });

        renderEditor('/admin/workflows/wf-1/edit');

        await waitFor(() => {
            expect(workflowsService.get).toHaveBeenCalledWith('wf-1');
        });

        expect(await screen.findByTestId('workflow-editor-page')).toBeInTheDocument();
        const nameInput = screen.getByTestId('workflow-editor-name') as HTMLInputElement;
        await waitFor(() => {
            expect(nameInput.value).toBe('My Flow');
        });
        expect(screen.getAllByText('notify').length).toBeGreaterThanOrEqual(1);
        expect(screen.getByTestId('rf__node-notify')).toBeInTheDocument();
    });

    it('shows error state with link back when get fails', async () => {
        vi.mocked(workflowsService.get).mockRejectedValue(new Error('Not found'));

        renderEditor('/admin/workflows/missing/edit');

        expect(await screen.findByTestId('workflow-editor-error')).toBeInTheDocument();
        expect(screen.getByText(/not found/i)).toBeInTheDocument();
        expect(screen.getByRole('link', { name: /back to workflows/i })).toHaveAttribute(
            'href',
            '/admin/workflows',
        );
    });

    it('calls create on save for new workflow', async () => {
        const user = userEvent.setup();
        vi.mocked(workflowsService.create).mockResolvedValue({
            id: 'new-id',
            account_id: 'AB1234',
            name: 'Created',
            description: null,
            trigger_type: 'manual',
            trigger_config: { type: 'manual' },
            steps: [],
            enabled: true,
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
            created_by: null,
        });

        renderEditor('/admin/workflows/new');

        await screen.findByTestId('workflow-editor-page');
        const nameInput = screen.getByTestId('workflow-editor-name');
        await user.clear(nameInput);
        await user.type(nameInput, 'Created');
        await user.click(screen.getByTestId('workflow-editor-save'));

        await waitFor(() => {
            expect(workflowsService.create).toHaveBeenCalled();
        });

        const payload = vi.mocked(workflowsService.create).mock.calls[0][0];
        expect(payload.name).toBe('Created');
        expect(payload.trigger).toEqual({ type: 'manual' });
        expect(payload.steps).toEqual([]);
        expect(payload.enabled).toBe(true);
    });

    it('calls update on save for edit workflow', async () => {
        const user = userEvent.setup();
        vi.mocked(workflowsService.get).mockResolvedValue({
            id: 'wf-2',
            account_id: 'AB1234',
            name: 'Old Name',
            description: null,
            trigger_type: 'manual',
            trigger_config: { type: 'manual' },
            steps: [
                {
                    type: 'action',
                    name: 's1',
                    action_type: 'send_webhook',
                    config: {},
                    position_x: 1,
                    position_y: 2,
                },
            ],
            enabled: true,
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
            created_by: null,
        });
        vi.mocked(workflowsService.update).mockResolvedValue({
            id: 'wf-2',
            account_id: 'AB1234',
            name: 'New Name',
            description: null,
            trigger_type: 'manual',
            trigger_config: { type: 'manual' },
            steps: [],
            enabled: true,
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
            created_by: null,
        });

        renderEditor('/admin/workflows/wf-2/edit');
        await waitFor(() => {
            expect(screen.getByTestId('workflow-editor-name')).toHaveValue('Old Name');
        });

        const nameInput = screen.getByTestId('workflow-editor-name');
        await user.clear(nameInput);
        await user.type(nameInput, 'New Name');
        await user.click(screen.getByTestId('workflow-editor-save'));

        await waitFor(() => {
            expect(workflowsService.update).toHaveBeenCalled();
        });

        const [id, payload] = vi.mocked(workflowsService.update).mock.calls[0];
        expect(id).toBe('wf-2');
        expect(payload.name).toBe('New Name');
        expect(payload.steps).toBeDefined();
        expect(payload.steps![0]).toMatchObject({
            name: 's1',
            position_x: 1,
            position_y: 2,
        });
    });
});
