/**
 * Smoke coverage for editor shells (merged with full editor behavior).
 * Create path is gated by template picker; edit loads via get.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@/test/utils';
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

vi.mock('@/hooks/use-toast', () => ({
    useToast: () => ({ toast: vi.fn() }),
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

describe('HookEditorPage shell smoke', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(getCollections).mockResolvedValue({
            items: [],
            total: 0,
            page: 1,
            page_size: 200,
        } as never);
        vi.mocked(emailService.listEmailTemplates).mockResolvedValue([]);
    });

    it('create route shows template picker without get', async () => {
        renderEditor('/admin/hooks/new');
        expect(await screen.findByTestId('hook-template-picker')).toBeInTheDocument();
        expect(hooksService.get).not.toHaveBeenCalled();
    });

    it('loads hook on edit and shows name input', async () => {
        vi.mocked(hooksService.get).mockResolvedValue({
            id: 'hk-1',
            account_id: 'AB1234',
            name: 'My Hook',
            description: null,
            trigger: { type: 'manual' },
            condition: null,
            actions: [],
            enabled: true,
            last_run_at: null,
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
            created_by: null,
        });

        renderEditor('/admin/hooks/hk-1/edit');
        expect(await screen.findByTestId('hook-editor-page')).toBeInTheDocument();
        expect(screen.getByTestId('hook-name-input')).toHaveValue('My Hook');
        expect(hooksService.get).toHaveBeenCalledWith('hk-1');
    });

    it('shows error + back for invalid id', async () => {
        vi.mocked(hooksService.get).mockRejectedValue(new Error('404'));
        renderEditor('/admin/hooks/missing/edit');
        expect(await screen.findByTestId('hook-editor-error')).toBeInTheDocument();
        expect(screen.getByText('Back to Hooks')).toBeInTheDocument();
    });
});
