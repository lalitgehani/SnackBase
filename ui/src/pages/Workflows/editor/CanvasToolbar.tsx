/**
 * Floating canvas toolbar: zoom, fit, auto-layout, delete, shortcuts help.
 * Must render inside ReactFlowProvider (sibling of ReactFlow is fine).
 */

import { useReactFlow } from '@xyflow/react';
import {
    ZoomIn,
    ZoomOut,
    Maximize2,
    LayoutGrid,
    Trash2,
    Keyboard,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from '@/components/ui/popover';
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from '@/components/ui/tooltip';
import { Separator } from '@/components/ui/separator';

interface Props {
    onAutoLayout: () => void;
    onDeleteSelected: () => void;
    canDelete: boolean;
    readOnly?: boolean;
}

function ToolButton({
    label,
    onClick,
    disabled,
    children,
    testId,
}: {
    label: string;
    onClick: () => void;
    disabled?: boolean;
    children: React.ReactNode;
    testId?: string;
}) {
    return (
        <Tooltip>
            <TooltipTrigger asChild>
                <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={onClick}
                    disabled={disabled}
                    aria-label={label}
                    data-testid={testId}
                >
                    {children}
                </Button>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="text-xs">
                {label}
            </TooltipContent>
        </Tooltip>
    );
}

export function CanvasToolbar({
    onAutoLayout,
    onDeleteSelected,
    canDelete,
    readOnly = false,
}: Props) {
    const { zoomIn, zoomOut, fitView } = useReactFlow();

    return (
        <TooltipProvider delayDuration={300}>
            <div
                className="absolute top-3 left-1/2 -translate-x-1/2 z-10 flex items-center gap-0.5 rounded-lg border bg-card/95 backdrop-blur shadow-sm px-1 py-0.5"
                data-testid="workflow-canvas-toolbar"
            >
                <ToolButton
                    label="Zoom in"
                    onClick={() => zoomIn({ duration: 150 })}
                    testId="toolbar-zoom-in"
                >
                    <ZoomIn className="h-4 w-4" />
                </ToolButton>
                <ToolButton
                    label="Zoom out"
                    onClick={() => zoomOut({ duration: 150 })}
                    testId="toolbar-zoom-out"
                >
                    <ZoomOut className="h-4 w-4" />
                </ToolButton>
                <ToolButton
                    label="Fit view"
                    onClick={() => fitView({ padding: 0.2, duration: 200 })}
                    testId="toolbar-fit-view"
                >
                    <Maximize2 className="h-4 w-4" />
                </ToolButton>

                {!readOnly && (
                    <>
                        <Separator orientation="vertical" className="h-5 mx-0.5" />
                        <ToolButton
                            label="Auto layout"
                            onClick={onAutoLayout}
                            testId="toolbar-auto-layout"
                        >
                            <LayoutGrid className="h-4 w-4" />
                        </ToolButton>
                        <ToolButton
                            label="Delete selected"
                            onClick={onDeleteSelected}
                            disabled={!canDelete}
                            testId="toolbar-delete"
                        >
                            <Trash2 className="h-4 w-4" />
                        </ToolButton>
                    </>
                )}

                <Separator orientation="vertical" className="h-5 mx-0.5" />

                <Popover>
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <PopoverTrigger asChild>
                                <Button
                                    type="button"
                                    variant="ghost"
                                    size="icon"
                                    className="h-8 w-8"
                                    aria-label="Keyboard shortcuts"
                                    data-testid="toolbar-shortcuts-help"
                                >
                                    <Keyboard className="h-4 w-4" />
                                </Button>
                            </PopoverTrigger>
                        </TooltipTrigger>
                        <TooltipContent side="bottom" className="text-xs">
                            Shortcuts
                        </TooltipContent>
                    </Tooltip>
                    <PopoverContent className="w-64 text-xs" align="center">
                        <p className="font-medium mb-2">Keyboard shortcuts</p>
                        <ul className="space-y-1.5 text-muted-foreground">
                            <li className="flex justify-between gap-2">
                                <span>Save</span>
                                <kbd className="font-mono text-[10px] bg-muted px-1.5 py-0.5 rounded">
                                    ⌘/Ctrl+S
                                </kbd>
                            </li>
                            <li className="flex justify-between gap-2">
                                <span>Delete selection</span>
                                <kbd className="font-mono text-[10px] bg-muted px-1.5 py-0.5 rounded">
                                    Del / ⌫
                                </kbd>
                            </li>
                            <li className="flex justify-between gap-2">
                                <span>Deselect</span>
                                <kbd className="font-mono text-[10px] bg-muted px-1.5 py-0.5 rounded">
                                    Esc
                                </kbd>
                            </li>
                        </ul>
                        <p className="mt-2 text-[10px] text-muted-foreground">
                            Shortcuts are ignored while typing in inputs.
                        </p>
                    </PopoverContent>
                </Popover>
            </div>
        </TooltipProvider>
    );
}

export default CanvasToolbar;
