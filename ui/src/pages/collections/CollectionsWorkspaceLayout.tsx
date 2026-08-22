/**
 * Collections workspace shell: browser rail + main outlet.
 */

import { useState } from 'react';
import { Outlet } from 'react-router';
import { Download, Upload } from 'lucide-react';
import { Button } from '@/components/ui/button';
import ImportCollectionsDialog from '@/components/collections/ImportCollectionsDialog';
import { exportCollections } from '@/services/collections.service';
import { handleApiError } from '@/lib/errors';
import { useToast } from '@/hooks/use-toast';
import { useCollectionsWorkspaceShortcuts } from '@/hooks/useCollectionsWorkspaceShortcuts';
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
    refreshCollections,
  } = useCollectionsWorkspace();
  const { toast } = useToast();
  const [isExporting, setIsExporting] = useState(false);

  useCollectionsWorkspaceShortcuts({ enabled: true });

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
