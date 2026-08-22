import type { SnackBaseClient } from '@snackbase/sdk'
import { isValidSlug } from '@/lib/slug'
import { getErrorMessage } from '@/lib/errors'
import { createEnvironmentWithRef } from '@/lib/control-plane/env-ref'
import type { Environment, Project, TenancyMode } from '@/types/control-plane'

export interface CreateEnvironmentInput {
  projectId: string
  name: string
  slug: string
  /** Inherit from project when omitted */
  region?: string
  tenancyMode?: TenancyMode
}

/**
 * Create an additional environment (e.g. staging) under a project.
 * Status starts as `pending` for the provision worker (which generates bootstrap secrets).
 */
export async function createEnvironment(
  client: SnackBaseClient,
  input: CreateEnvironmentInput,
): Promise<Environment> {
  const name = input.name.trim()
  const slug = input.slug.trim().toLowerCase()
  const projectId = input.projectId.trim()

  if (!projectId) throw new Error('Project is required')
  if (!name) throw new Error('Environment name is required')
  if (!slug) throw new Error('Environment slug is required')
  if (!isValidSlug(slug)) {
    throw new Error(
      'Slug must be lowercase letters, numbers, and hyphens only (e.g. staging)',
    )
  }

  const project = await client.records.get<Project>('projects', projectId)
  const region = (input.region ?? project.region ?? '').trim()
  const tenancyMode = input.tenancyMode ?? project.tenancy_mode

  if (!region) throw new Error('Region is required (inherit from project)')
  if (tenancyMode !== 'single' && tenancyMode !== 'multi') {
    throw new Error('Tenancy mode must be single or multi')
  }

  const existing = await client.records.list<Environment>('environments', {
    filter: `project = "${projectId}" && slug = "${slug}"`,
    limit: 1,
  })
  const live = (existing.items ?? []).filter((e) => e.status !== 'deleted')
  if (live.length > 0) {
    throw new Error(
      `An environment with slug "${slug}" already exists on this project.`,
    )
  }

  try {
    return await createEnvironmentWithRef(
      (data) => client.records.create<Environment>('environments', data),
      {
        project: projectId,
        name,
        slug,
        status: 'pending',
        region,
        tenancy_mode: tenancyMode,
      },
    )
  } catch (err) {
    throw new Error(getErrorMessage(err, 'Failed to create environment'))
  }
}
