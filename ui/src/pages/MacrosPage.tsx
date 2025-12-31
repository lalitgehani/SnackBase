import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { CodeXml, Search, RefreshCw, Plus } from 'lucide-react';
import MacrosTable from '@/components/macros/MacrosTable';
import MacroEditorDialog from '@/components/macros/MacroEditorDialog';
import MacroTestDialog from '@/components/macros/MacroTestDialog';
import MacroDetailDialog from '@/components/macros/MacroDetailDialog';
import DeleteMacroDialog from '@/components/macros/DeleteMacroDialog';
import { listMacros, deleteMacro, createMacro, updateMacro } from '@/services/macros.service';
import type { Macro, MacroCreate, MacroUpdate } from '@/types/macro';
import { handleApiError } from '@/lib/api';

export default function MacrosPage() {
    const [macros, setMacros] = useState<Macro[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [searchQuery, setSearchQuery] = useState('');

    // Dialog states
    const [editorOpen, setEditorOpen] = useState(false);
    const [testOpen, setTestOpen] = useState(false);
    const [detailOpen, setDetailOpen] = useState(false);
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [selectedMacro, setSelectedMacro] = useState<Macro | null>(null);

    const fetchMacros = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await listMacros();
            setMacros(data);
        } catch (err) {
            setError(handleApiError(err));
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchMacros();
    }, []);

    const handleDelete = (macro: Macro) => {
        setSelectedMacro(macro);
        setDeleteDialogOpen(true);
    };

    const handleDeleteConfirm = async (macroId: number) => {
        await deleteMacro(macroId);
        fetchMacros();
    };

    const handleView = (macro: Macro) => {
        setSelectedMacro(macro);
        setDetailOpen(true);
    };

    const handleEdit = (macro: Macro) => {
        setSelectedMacro(macro);
        setEditorOpen(true);
    };

    const handleTest = (macro: Macro) => {
        setSelectedMacro(macro);
        setTestOpen(true);
    };

    const handleCreate = () => {
        setSelectedMacro(null);
        setEditorOpen(true);
    };

    const handleEditorSubmit = async (data: MacroCreate | MacroUpdate) => {
        if (selectedMacro) {
            await updateMacro(selectedMacro.id, data as MacroUpdate);
        } else {
            await createMacro(data as MacroCreate);
        }
        fetchMacros();
    };

    const filteredMacros = macros.filter((macro) =>
        macro.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (macro.description || '').toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold">Macros</h1>
                    <p className="text-muted-foreground mt-2">
                        Manage SQL macros for custom permission logic
                    </p>
                </div>
                <div className="flex gap-2">
                    <Button
                        variant="outline"
                        onClick={fetchMacros}
                        disabled={loading}
                        className="gap-2"
                    >
                        <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                        Refresh
                    </Button>
                    <Button onClick={handleCreate} className="gap-2">
                        <Plus className="h-4 w-4" />
                        Create Macro
                    </Button>
                </div>
            </div>

            <Card>
                <CardHeader className="pb-3">
                    <CardTitle className="flex items-center gap-2">
                        <CodeXml className="h-5 w-5 text-primary" />
                        Macro Library
                    </CardTitle>
                    <CardDescription>
                        Custom SQL snippets that can be referenced as @macro_name in permission rules
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="flex gap-2">
                        <div className="relative flex-1">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                            <Input
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                placeholder="Search macros by name or description..."
                                className="pl-9"
                            />
                        </div>
                    </div>

                    {error && (
                        <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
                            <p className="text-destructive font-medium">Failed to load macros</p>
                            <p className="text-sm text-muted-foreground mt-1">{error}</p>
                            <Button onClick={fetchMacros} className="mt-4" size="sm">
                                Try Again
                            </Button>
                        </div>
                    )}

                    {loading && macros.length === 0 ? (
                        <div className="flex items-center justify-center py-12">
                            <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
                        </div>
                    ) : (
                        <MacrosTable
                            macros={filteredMacros}
                            onView={handleView}
                            onEdit={handleEdit}
                            onDelete={handleDelete}
                            onTest={handleTest}
                        />
                    )}
                </CardContent>
            </Card>

            {/* Dialogs */}
            <MacroEditorDialog
                open={editorOpen}
                onOpenChange={setEditorOpen}
                onSubmit={handleEditorSubmit}
                macro={selectedMacro}
            />

            <MacroTestDialog
                open={testOpen}
                onOpenChange={setTestOpen}
                macro={selectedMacro}
            />

            <MacroDetailDialog
                open={detailOpen}
                onOpenChange={setDetailOpen}
                macro={selectedMacro}
                onTest={handleTest}
                onEdit={handleEdit}
            />

            <DeleteMacroDialog
                open={deleteDialogOpen}
                onOpenChange={setDeleteDialogOpen}
                macro={selectedMacro}
                onConfirm={handleDeleteConfirm}
            />
        </div>
    );
}
