import type { SnackBaseClient } from '@snackbase/sdk';
import { createServiceHook } from '@/lib/snackbase/createServiceHook';
import { bindService } from '@/lib/snackbase/bindService';

export type JobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'retrying' | 'dead';

export interface Job {
  id: string;
  queue: string;
  handler: string;
  payload: Record<string, unknown>;
  status: JobStatus;
  priority: number;
  run_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  failed_at: string | null;
  error_message: string | null;
  attempt_number: number;
  max_retries: number;
  retry_delay_seconds: number;
  created_at: string;
  created_by: string | null;
  account_id: string | null;
}

export interface JobListResponse {
  items: Job[];
  total: number;
}

export interface JobStats {
  pending: number;
  running: number;
  completed: number;
  failed: number;
  retrying: number;
  dead: number;
  avg_duration_seconds: number | null;
  failure_rate: number | null;
}

export interface JobListParams {
  status?: string;
  queue?: string;
  handler?: string;
  limit?: number;
  offset?: number;
}

export function createJobsService(client: SnackBaseClient) {
  return {
    list: (params?: JobListParams) => client.jobs.list(params),
    getStats: () => client.jobs.stats(),
    retry: (id: string) => client.jobs.retry(id),
    cancel: (id: string) => client.jobs.cancel(id),
  };
}

export const useJobsService = createServiceHook(createJobsService);
export const jobsService = bindService(createJobsService);
