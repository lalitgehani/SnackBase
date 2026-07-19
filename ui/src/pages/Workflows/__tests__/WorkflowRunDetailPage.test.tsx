import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@/test/utils';
import { Route, Routes } from 'react-router';
import WorkflowRunDetailPage from '../WorkflowRunDetailPage';
import { workflowsService } from '@/services/workflows.service';

vi.mock('@/services/workflows.service', () => ({
    workflowsService: {
        get: vi.fn(),
        getInstance: vi.fn(),
        cancelInstance: vi.fn(),
        resumeInstance: vi.fn(),
    },
}));

vi.mock('@/hooks/use-toast', () => ({
    useToast: () => ({ toast: vi.fn() }),
}));

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
    description: null,
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
            next: 'step_b',
        },
        {
            type: 'action',
            name: 'step_b',
            action_type: 'send_email',
            config: {},
            position_x: 300,
            position_y: 0,
        },
    ],
    enabled: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    created_by: null,
};

const failedInstance = {
    id: 'inst-1',
    workflow_id: 'wf-1',
    account_id: 'AB1234',
    status: 'failed' as const,
    current_step: 'step_b',
    context: {},
    started_at: '2026-01-01T00:00:00Z',
    completed_at: '2026-01-01T00:00:10Z',
    error_message: 'Instance failed',
    resume_job_id: null,
    step_logs: [
        {
            id: 'log-1',
            instance_id: 'inst-1',
            workflow_id: 'wf-1',
            account_id: 'AB1234',
            step_name: 'step_a',
            step_type: 'action',
            status: 'success',
            input: { action_type: 'send_webhook' },
            output: { ok: true },
            error_message: null,
            started_at: '2026-01-01T00:00:00Z',
            completed_at: '2026-01-01T00:00:01Z',
        },
        {
            id: 'log-2',
            instance_id: 'inst-1',
            workflow_id: 'wf-1',
            account_id: 'AB1234',
            step_name: 'step_b',
            step_type: 'action',
            status: 'failed',
            input: { action_type: 'send_email' },
            output: null,
            error_message: 'SMTP down',
            started_at: '2026-01-01T00:00:02Z',
            completed_at: '2026-01-01T00:00:03Z',
        },
    ],
};

function renderRun() {
    return render(
        <Routes>
            <Route
                path="/admin/workflows/:id/runs/:instanceId"
                element={<WorkflowRunDetailPage />}
            />
            <Route path="/admin/workflows/:id" element={<div>Overview</div>} />
        </Routes>,
        { initialEntries: ['/admin/workflows/wf-1/runs/inst-1'] },
    );
}

describe('WorkflowRunDetailPage', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(workflowsService.get).mockResolvedValue(sampleWorkflow);
        vi.mocked(workflowsService.getInstance).mockResolvedValue(failedInstance);
    });

    it('loads run and overlays failed status on nodes', async () => {
        renderRun();
        expect(await screen.findByTestId('workflow-run-detail-page')).toBeInTheDocument();
        expect(workflowsService.get).toHaveBeenCalledWith('wf-1');
        expect(workflowsService.getInstance).toHaveBeenCalledWith('inst-1');

        // Failed step has run status badge
        const statusBadges = await screen.findAllByTestId('workflow-node-run-status');
        const texts = statusBadges.map((el) => el.textContent);
        expect(texts).toContain('failed');
        expect(texts).toContain('completed');

        const allActions = screen.getAllByTestId('workflow-node-action');
        const failed = allActions.find((n) => n.getAttribute('data-run-status') === 'failed');
        const completed = allActions.find((n) => n.getAttribute('data-run-status') === 'completed');
        expect(failed).toBeTruthy();
        expect(completed).toBeTruthy();
    });

    it('shows instance error and resume control for failed runs', async () => {
        renderRun();
        await screen.findByTestId('workflow-run-detail-page');

        expect(screen.getByTestId('instance-error')).toHaveTextContent('Instance failed');
        expect(screen.getByTestId('run-resume-btn')).toBeInTheDocument();
        // Overlay shows failed styling on the failed step node
        const allActions = screen.getAllByTestId('workflow-node-action');
        expect(
            allActions.some((n) => n.getAttribute('data-run-status') === 'failed'),
        ).toBe(true);
    });

    it('shows graph when instance has no step logs', async () => {
        vi.mocked(workflowsService.getInstance).mockResolvedValue({
            ...failedInstance,
            status: 'pending',
            current_step: null,
            error_message: null,
            step_logs: [],
        });
        renderRun();
        expect(await screen.findByTestId('workflow-run-detail-page')).toBeInTheDocument();
        expect(screen.getByTestId('workflow-canvas')).toBeInTheDocument();
        // Nodes present without run status badges (trigger may also lack)
        expect(screen.getAllByTestId('workflow-node-action').length).toBe(2);
    });

    it('errors when instance workflow_id mismatches', async () => {
        vi.mocked(workflowsService.getInstance).mockResolvedValue({
            ...failedInstance,
            workflow_id: 'other-wf',
        });
        renderRun();
        expect(await screen.findByTestId('run-detail-error')).toBeInTheDocument();
    });
});
