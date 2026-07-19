import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { NodePalette } from '../palette/NodePalette';

describe('NodePalette', () => {
    it('renders step items and click-to-add invokes onAddStep', async () => {
        const user = userEvent.setup();
        const onAddStep = vi.fn();
        render(<NodePalette onAddStep={onAddStep} />);

        expect(screen.getByTestId('workflow-editor-palette')).toHaveAttribute(
            'aria-label',
            'Step palette',
        );
        expect(screen.getByTestId('palette-item-action')).toHaveAttribute(
            'aria-label',
            'Add Action step',
        );

        await user.click(screen.getByTestId('palette-item-action'));
        expect(onAddStep).toHaveBeenCalledWith('action');

        await user.click(screen.getByTestId('palette-item-condition'));
        expect(onAddStep).toHaveBeenCalledWith('condition');
    });

    it('filters by search query', async () => {
        const user = userEvent.setup();
        render(<NodePalette onAddStep={vi.fn()} />);

        await user.type(screen.getByTestId('workflow-palette-search'), 'loop');
        expect(screen.getByTestId('palette-item-loop')).toBeInTheDocument();
        expect(screen.queryByTestId('palette-item-action')).not.toBeInTheDocument();
    });

    it('disables items when readOnly', async () => {
        const user = userEvent.setup();
        const onAddStep = vi.fn();
        render(<NodePalette onAddStep={onAddStep} readOnly />);

        const btn = screen.getByTestId('palette-item-action');
        expect(btn).toBeDisabled();
        await user.click(btn);
        expect(onAddStep).not.toHaveBeenCalled();
    });
});
