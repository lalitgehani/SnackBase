/**
 * Collections workspace shell: browser rail + main outlet.
 */

import { useState } from 'react';
import { Outlet } from 'react-router';
import { Download, Upload } from 'lucide-react';
import { Button } from '@/components/ui/button';
import CreateCollectionDialog from '@/components/collections/CreateCollectionDialog';
import ImportCollectionsDialog from '@/components/collections/ImportCollectionsDialog';
import {
  createCollection,
  exportCollections,
  type CreateCollectionData,
} from '@/services/collections.service';
import { handleApiError } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import {
  CollectionsWorkspaceProvider,
  useCollectionsWorkspace,
} from './CollectionsWorkspaceContext';
import CollectionBrowserRail from './CollectionBrowserRail';

function WorkspaceChrome() {
  const {
    isSuperadmin,
    importDialogOpen,
    setImportDialogOpen,
    createDialogOpen,
    setCreateDialogOpen,
    collectionNames,
    refreshCollections,
  } = useCollectionsWorkspace();
  const { toast } = useToast();
  const [isExporting, setIsExporting] = useState(false);

  const handleCreate = async (data: CreateCollectionData) => {
    await createCollection(data);
    await refreshCollections();
  };

  const handleExport = async () => {
    setIsExporting(true);
    try {
      await exportCollections();
      toast({
        title: 'Export successful',
        description: 'Collections exported to JSON file',
      });
    } catch (err) {
      toast({
        variant: 'destructive',
        title: 'Export failed',
        description: handleApiError(err),
      });
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div
      className="flex h-full min-h-0 flex-1 overflow-hidden"
      data-testid="collections-workspace"
    >
      <CollectionBrowserRail />
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        {isSuperadmin && (
          <div className="flex shrink-0 items-center justify-end gap-2 border-b bg-background px-4 py-2">
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5"
              onClick={() => void handleExport()}
              disabled={isExporting}
            >
              <Download className="h-3.5 w-3.5" />
              {isExporting ? 'Exporting…' : 'Export JSON'}
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5"
              onClick={() => setImportDialogOpen(true)}
            >
              <Upload className="h-3.5 w-3.5" />
              Import JSON
            </Button>
          </div>
        )}
        <div className="min-h-0 flex-1 overflow-y-auto">
          <Outlet />
        </div>
      </div>

      <CreateCollectionDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onSubmit={handleCreate}
        collections={collectionNames}
      />

      <ImportCollectionsDialog
        open={importDialogOpen}
        onOpenChange={setImportDialogOpen}
        onSuccess={() => void refreshCollections()}
      />
    </div>
  );
}

export default function CollectionsWorkspaceLayout() {
  return (
    <CollectionsWorkspaceProvider>
      <WorkspaceChrome />
    </CollectionsWorkspaceProvider>
  );
}
