import type { SnackBaseClient } from '@snackbase/sdk'
import { getErrorMessage } from '@/lib/errors'
import type { Environment } from '@/types/control-plane'

/**
 * Re-queue a failed environment for provisioning (worker picks up `pending`).
 */
export async function retryProvision(
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
        status: 'pending',
        error_message: null,
      },
    )
  } catch (err) {
    throw new Error(getErrorMessage(err, 'Failed to retry provision'))
  }
}
