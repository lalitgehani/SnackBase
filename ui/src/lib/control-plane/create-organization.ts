import type { SnackBaseClient } from '@snackbase/sdk'
import { isValidSlug } from '@/lib/slug'
import { getErrorMessage } from '@/lib/errors'
import type { Organization } from '@/types/control-plane'

export interface CreateOrganizationInput {
  name: string
  slug: string
}

export interface CreateOrganizationResult {
  organization: Organization
}

function friendlyOrgError(err: unknown): Error {
  const msg = getErrorMessage(err, 'Failed to create organization')
  const lower = msg.toLowerCase()
  if (
    lower.includes('unique') ||
    lower.includes('duplicate') ||
    lower.includes('already exists') ||
    lower.includes('409')
  ) {
    return new Error('An organization with this slug already exists. Choose a different slug.')
  }
  return err instanceof Error ? err : new Error(msg)
}

export async function createOrganization(
  client: SnackBaseClient,
  input: CreateOrganizationInput,
): Promise<CreateOrganizationResult> {
  const name = input.name.trim()
  const slug = input.slug.trim().toLowerCase()

  if (!name) {
    throw new Error('Organization name is required')
  }
  if (!slug) {
    throw new Error('Organization slug is required')
  }
  if (!isValidSlug(slug)) {
    throw new Error(
      'Slug must be lowercase letters, numbers, and hyphens only (e.g. my-team)',
    )
  }

  try {
    const organization = await client.records.create<Organization>('organizations', {
      name,
      slug,
      status: 'active',
    })
    return { organization }
  } catch (err) {
    throw friendlyOrgError(err)
  }
}
