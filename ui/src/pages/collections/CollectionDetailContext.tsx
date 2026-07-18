/**
 * Outlet context for collection detail tabs (full collection + list metadata).
 */

import { createContext, useContext, type ReactNode } from 'react';
import type {
  Collection,
  CollectionListItem,
} from '@/services/collections.service';

export interface CollectionDetailContextValue {
  collection: Collection | null;
  listItem: CollectionListItem | undefined;
  collectionName: string;
  loading: boolean;
  error: string | null;
  refreshDetail: () => Promise<void>;
}

const CollectionDetailContext = createContext<CollectionDetailContextValue | null>(
  null,
);

export function CollectionDetailProvider({
  value,
  children,
}: {
  value: CollectionDetailContextValue;
  children: ReactNode;
}) {
  return (
    <CollectionDetailContext.Provider value={value}>
      {children}
    </CollectionDetailContext.Provider>
  );
}

// Context hooks are co-located with providers (standard React pattern).
// eslint-disable-next-line react-refresh/only-export-components
export function useCollectionDetail() {
  const ctx = useContext(CollectionDetailContext);
  if (!ctx) {
    throw new Error('useCollectionDetail must be used within CollectionDetailProvider');
  }
  return ctx;
}
