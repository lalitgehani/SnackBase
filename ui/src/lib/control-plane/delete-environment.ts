import type { SnackBaseClient } from '@snackbase/sdk'
import { getErrorMessage } from '@/lib/errors'
import type { Environment } from '@/types/control-plane'

/**
 * Soft-delete: mark environment `deleting` so the provision worker cleans the
 * data plane, then transitions to `deleted`. Does not hard-delete the row.
 */
export async function requestEnvironmentDelete(
  client: SnackBaseClient,
  environmentId: string,
): Promise<Environment> {
  if (!environmentId.trim()) {
    throw new Error('Environment id is required')
  }
  try {
    return await client.records.patch<Environment>(
      'environments',
      environmentId,
      {
        status: 'deleting',
      },
    )
  } catch (err) {
    throw new Error(getErrorMessage(err, 'Failed to delete environment'))
  }
}

/**
 * Archive project and mark remaining environments for deprovision.
 */
export async function archiveProjectWithEnvironments(
  client: SnackBaseClient,
  projectId: string,
  environments: Environment[],
): Promise<void> {
  const toDelete = environments.filter(
    (e) => e.status !== 'deleted' && e.status !== 'deleting',
  )
  for (const env of toDelete) {
    await requestEnvironmentDelete(client, env.id)
  }
  try {
    await client.records.patch('projects', projectId, {
      status: 'archived',
    })
  } catch (err) {
    throw new Error(getErrorMessage(err, 'Failed to archive project'))
  }
}
