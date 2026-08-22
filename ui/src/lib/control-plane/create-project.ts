import type { SnackBaseClient } from '@snackbase/sdk'
import { isValidSlug } from '@/lib/slug'
import { getErrorMessage } from '@/lib/errors'
import { isRegionAvailable, listAvailableRegions } from '@/lib/control-plane/regions'
import { createEnvironmentWithRef } from '@/lib/control-plane/env-ref'
import type { Environment, Project, TenancyMode } from '@/types/control-plane'

export interface CreateProjectInput {
  organizationId: string
  name: string
  slug: string
  region: string
  tenancyMode: TenancyMode
}

export interface CreateProjectResult {
  project: Project
  environment: Environment
}

const TENANCY_MODES: TenancyMode[] = ['single', 'multi']

function friendlyProjectError(err: unknown): Error {
  const msg = getErrorMessage(err, 'Failed to create project')
  const lower = msg.toLowerCase()
  if (
    lower.includes('unique') ||
    lower.includes('duplicate') ||
    lower.includes('already exists') ||
    lower.includes('409')
  ) {
    return new Error(
      'A project with this slug already exists. Project slugs must be globally unique.',
    )
  }
  return err instanceof Error ? err : new Error(msg)
}

/**
 * Create a project and the default production environment.
 *
 * Bootstrap secrets are generated later by the provision worker (not by Console).
 * Phase 3 uses a validated client multi-call (not atomic). Documented in
 * control-plane SCHEMA.md until a product endpoint can chain create_record IDs.
 */
export async function createProject(
  client: SnackBaseClient,
  input: CreateProjectInput,
): Promise<CreateProjectResult> {
  const name = input.name.trim()
  const slug = input.slug.trim().toLowerCase()
  const region = input.region.trim()
  const tenancyMode = input.tenancyMode
  const organizationId = input.organizationId.trim()

  if (!organizationId) {
    throw new Error('Organization is required')
  }
  if (!name) {
    throw new Error('Project name is required')
  }
  if (!slug) {
    throw new Error('Project slug is required')
  }
  if (!isValidSlug(slug)) {
    throw new Error(
      'Slug must be lowercase letters, numbers, and hyphens only (e.g. my-api)',
    )
  }
  if (!region) {
    throw new Error('Region is required')
  }
  if (!TENANCY_MODES.includes(tenancyMode)) {
    throw new Error('Tenancy mode must be single or multi')
  }

  const regions = await listAvailableRegions(client)
  if (!isRegionAvailable(regions, region)) {
    throw new Error(
      `Region "${region}" is not available. Choose a region from the catalog.`,
    )
  }

  let project: Project
  try {
    project = await client.records.create<Project>('projects', {
      organization: organizationId,
      name,
      slug,
      region,
      tenancy_mode: tenancyMode,
      status: 'active',
    })
  } catch (err) {
    throw friendlyProjectError(err)
  }

  try {
    const environment = await createEnvironmentWithRef(
      (data) => client.records.create<Environment>('environments', data),
      {
        project: project.id,
        name: 'Production',
        slug: 'production',
        status: 'pending',
        region,
        tenancy_mode: tenancyMode,
      },
    )
    return { project, environment }
  } catch (envErr) {
    // Best-effort compensate: delete project if caller is admin
    try {
      await client.records.delete('projects', project.id)
    } catch {
      // leave orphan project; surface env error
    }
    throw new Error(
      `Project was created but the production environment failed: ${getErrorMessage(envErr)}. Try again or contact support.`,
    )
  }
}
