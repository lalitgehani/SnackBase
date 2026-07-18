/**
 * /admin/collections/new — opens create dialog; navigates on close.
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import CreateCollectionDialog from '@/components/collections/CreateCollectionDialog';
import {
  createCollection,
  type CreateCollectionData,
} from '@/services/collections.service';
import { useCollectionsWorkspace } from './CollectionsWorkspaceContext';

export default function CollectionNewPage() {
  const navigate = useNavigate();
  const { collectionNames, refreshCollections, isSuperadmin } =
    useCollectionsWorkspace();
  const [open, setOpen] = useState(true);
  const [createdName, setCreatedName] = useState<string | null>(null);

  useEffect(() => {
    if (!isSuperadmin) {
      navigate('/admin/collections', { replace: true });
    }
  }, [isSuperadmin, navigate]);

  const handleSubmit = async (data: CreateCollectionData) => {
    await createCollection(data);
    setCreatedName(data.name);
    await refreshCollections();
  };

  const handleOpenChange = (next: boolean) => {
    setOpen(next);
    if (!next) {
      if (createdName) {
        navigate(`/admin/collections/${createdName}`, { replace: true });
      } else {
        navigate('/admin/collections', { replace: true });
      }
    }
  };

  if (!isSuperadmin) {
    return null;
  }

  return (
    <div className="flex flex-1 items-center justify-center p-8 text-muted-foreground text-sm">
      <CreateCollectionDialog
        open={open}
        onOpenChange={handleOpenChange}
        onSubmit={handleSubmit}
        collections={collectionNames}
      />
      Creating a new collection…
    </div>
  );
}
