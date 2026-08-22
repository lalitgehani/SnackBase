/**
 * Shared state for the Collections workspace shell.
 * Provides collection list, rail collapse, and import dialog orchestration.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import {
  getCollections,
  type CollectionListItem,
} from '@/services/collections.service';
import { handleApiError } from '@/lib/errors';
import { isSuperadminAccount } from '@/lib/auth';
import { useAuthStore } from '@/stores/auth.store';

interface CollectionsWorkspaceContextValue {
  collections: CollectionListItem[];
  loading: boolean;
  error: string | null;
  refreshCollections: () => Promise<void>;
  railCollapsed: boolean;
  setRailCollapsed: (collapsed: boolean) => void;
  isSuperadmin: boolean;
  importDialogOpen: boolean;
  setImportDialogOpen: (open: boolean) => void;
  collectionNames: string[];
  getListItem: (name: string) => CollectionListItem | undefined;
}

const CollectionsWorkspaceContext = createContext<CollectionsWorkspaceContextValue | null>(
  null,
);

const RAIL_COLLAPSED_KEY = 'snackbase_collections_rail_collapsed';

export function CollectionsWorkspaceProvider({ children }: { children: ReactNode }) {
  const { account } = useAuthStore();
  // Superadmin = system account membership (backend require_superadmin), not role name.
  // Superadmins are seeded with role "admin" on the system account.
  const isSuperadmin = isSuperadminAccount(account);

  const [collections, setCollections] = useState<CollectionListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [railCollapsed, setRailCollapsedState] = useState(() => {
    if (typeof window === 'undefined') return false;
    return localStorage.getItem(RAIL_COLLAPSED_KEY) === 'true';
  });
  const [importDialogOpen, setImportDialogOpen] = useState(false);

  const setRailCollapsed = useCallback((collapsed: boolean) => {
    setRailCollapsedState(collapsed);
    localStorage.setItem(RAIL_COLLAPSED_KEY, String(collapsed));
  }, []);

  const refreshCollections = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getCollections({
        page: 1,
        page_size: 100,
        sort_by: 'name',
        sort_order: 'asc',
      });
      setCollections(response.items);
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshCollections();
  }, [refreshCollections]);

  const collectionNames = useMemo(
    () => collections.map((c) => c.name),
    [collections],
  );

  const getListItem = useCallback(
    (name: string) => collections.find((c) => c.name === name),
    [collections],
  );

  const value = useMemo<CollectionsWorkspaceContextValue>(
    () => ({
      collections,
      loading,
      error,
      refreshCollections,
      railCollapsed,
      setRailCollapsed,
      isSuperadmin,
      importDialogOpen,
      setImportDialogOpen,
      collectionNames,
      getListItem,
    }),
    [
      collections,
      loading,
      error,
      refreshCollections,
      railCollapsed,
      setRailCollapsed,
      isSuperadmin,
      importDialogOpen,
      collectionNames,
      getListItem,
    ],
  );

  return (
    <CollectionsWorkspaceContext.Provider value={value}>
      {children}
    </CollectionsWorkspaceContext.Provider>
  );
}

// Context hooks are co-located with providers (standard React pattern).
// eslint-disable-next-line react-refresh/only-export-components
export function useCollectionsWorkspace() {
  const ctx = useContext(CollectionsWorkspaceContext);
  if (!ctx) {
    throw new Error(
      'useCollectionsWorkspace must be used within CollectionsWorkspaceProvider',
    );
  }
  return ctx;
}
