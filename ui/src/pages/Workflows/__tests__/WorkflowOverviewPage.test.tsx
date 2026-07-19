import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/utils';
import { Route, Routes } from 'react-router';
import WorkflowOverviewPage from '../WorkflowOverviewPage';
import { workflowsService } from '@/services/workflows.service';

vi.mock('@/services/workflows.service', () => ({
    workflowsService: {
        get: vi.fn(),
        listInstances: vi.fn(),
        trigger: vi.fn(),
    },
}));

vi.mock('@/hooks/use-toast', () => ({
    useToast: () => ({ toast: vi.fn() }),
}));

// React Flow needs ResizeObserver
class ResizeObserverMock {
    observe() {}
    unobserve() {}
    disconnect() {}
}
vi.stubGlobal('ResizeObserver', ResizeObserverMock);

const sampleWorkflow = {
    id: 'wf-1',
    account_id: 'AB1234',
    name: 'Alpha Flow',
    description: 'Does things',
    trigger_type: 'manual',
    trigger_config: { type: 'manual' as const },
    steps: [
        {
            type: 'action',
            name: 'step_a',
            action_type: 'send_webhook',
            config: {},
            position_x: 100,
            position_y: 0,
        },
    ],
    enabled: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    created_by: null,
};

function renderOverview() {
    return render(
        <Routes>
            <Route path="/admin/workflows/:id" element={<WorkflowOverviewPage />} />
            <Route path="/admin/workflows/:id/edit" element={<div>Edit page</div>} />
            <Route
                path="/admin/workflows/:id/runs/:instanceId"
                element={<div>Run page</div>}
            />
            <Route path="/admin/workflows" element={<div>List</div>} />
        </Routes>,
        { initialEntries: ['/admin/workflows/wf-1'] },
    );
}

describe('WorkflowOverviewPage', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(workflowsService.get).mockResolvedValue(sampleWorkflow);
        vi.mocked(workflowsService.listInstances).mockResolvedValue({
            items: [
                {
                    id: 'inst-1',
                    workflow_id: 'wf-1',
                    account_id: 'AB1234',
                    status: 'failed',
                    current_step: 'step_a',
                    context: {},
                    started_at: '2026-01-01T00:00:00Z',
                    completed_at: '2026-01-01T00:00:10Z',
                    error_message: 'boom',
                    resume_job_id: null,
                },
            ],
            total: 1,
        });
    });

    it('loads workflow and recent instances', async () => {
        renderOverview();
        expect(await screen.findByTestId('workflow-overview-page')).toBeInTheDocument();
        expect(screen.getByTestId('overview-name')).toHaveTextContent('Alpha Flow');
        expect(workflowsService.get).toHaveBeenCalledWith('wf-1');
        expect(workflowsService.listInstances).toHaveBeenCalled();
        expect(await screen.findByTestId('instance-row-inst-1')).toBeInTheDocument();
        expect(screen.getByTestId('workflow-canvas')).toBeInTheDocument();
    });

    it('Edit button navigates to edit route', async () => {
        renderOverview();
        await screen.findByTestId('workflow-overview-page');
        const edit = screen.getByTestId('overview-edit');
        expect(edit).toHaveAttribute('href', '/admin/workflows/wf-1/edit');
    });

    it('shows error when get fails', async () => {
        vi.mocked(workflowsService.get).mockRejectedValue(new Error('nope'));
        renderOverview();
        expect(await screen.findByTestId('workflow-overview-error')).toBeInTheDocument();
    });
});
