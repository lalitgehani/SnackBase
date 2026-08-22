import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface ActiveOrg {
  id: string
  name: string
  slug: string
}

interface OrgContextState {
  activeOrg: ActiveOrg | null
  setActiveOrg: (org: ActiveOrg | null) => void
  clearActiveOrg: () => void
}

/**
 * Session-persisted active organization context for project lists.
 * URL remains source of truth when `:orgId` is present; store covers switcher + nav.
 */
export const useOrgContextStore = create<OrgContextState>()(
  persist(
    (set) => ({
      activeOrg: null,
      setActiveOrg: (org) => set({ activeOrg: org }),
      clearActiveOrg: () => set({ activeOrg: null }),
    }),
    {
      name: 'snackbase-cloud.org-context',
      partialize: (state) => ({ activeOrg: state.activeOrg }),
    },
  ),
)
