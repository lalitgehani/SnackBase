/**
 * Control-plane collection record shapes (Phase 1 schema).
 */

export type EnvironmentStatus =
  | 'pending'
  | 'provisioning'
  | 'ready'
  | 'failed'
  | 'deleting'
  | 'deleted'

export type TenancyMode = 'single' | 'multi'

export type OrgStatus = 'active' | 'archived'

export type ProjectStatus = 'active' | 'archived'

export type RegionStatus = 'available' | 'capacity' | 'unavailable'

export interface Organization {
  id: string
  name: string
  slug: string
  status: OrgStatus
  created_at?: string
  updated_at?: string
}

export interface Project {
  id: string
  organization: string
  name: string
  slug: string
  region: string
  tenancy_mode: TenancyMode
  status: ProjectStatus
  created_at?: string
  updated_at?: string
}

export interface Environment {
  id: string
  project: string
  name: string
  slug: string
  /** Stable 20-char URL identity for platform proxy / Studio routes */
  ref?: string
  status: EnvironmentStatus
  instance_url?: string | null
  error_message?: string | null
  data_plane_project_id?: string | null
  region?: string | null
  tenancy_mode?: TenancyMode | null
  snackbase_secret_key?: string | null
  snackbase_token_secret?: string | null
  snackbase_encryption_key?: string | null
  snackbase_superadmin_email?: string | null
  snackbase_superadmin_password?: string | null
  created_at?: string
  updated_at?: string
}

export interface Region {
  id: string
  code: string
  name: string
  country: string
  status: RegionStatus
  sort_order?: number | null
  created_at?: string
  updated_at?: string
}
