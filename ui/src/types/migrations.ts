export interface MigrationRevision {
  revision: string;
  description: string;
  down_revision: string | null;
  branch_labels: string[] | null;
  is_applied: boolean;
  is_head: boolean;
  is_dynamic: boolean;
  created_at: string | null;
}

export interface MigrationListResponse {
  revisions: MigrationRevision[];
  total: number;
  current_revision: string | null;
}

export interface CurrentRevisionResponse {
  revision: string;
  description: string;
  created_at: string | null;
}

export interface MigrationHistoryItem {
  revision: string;
  description: string;
  is_dynamic: boolean;
  created_at: string | null;
}

export interface MigrationHistoryResponse {
  history: MigrationHistoryItem[];
  total: number;
}
