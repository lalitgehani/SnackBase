import { Badge } from '@/components/ui/badge'
import type { TenancyMode } from '@/types/control-plane'

export interface ProjectMetaBadgesProps {
  region?: string | null
  tenancyMode?: TenancyMode | string | null
}

/** Region + tenancy mode chips for project cards (Supabase-style density). */
export function ProjectMetaBadges({ region, tenancyMode }: ProjectMetaBadgesProps) {
  return (
    <div className="flex flex-wrap items-center gap-1.5" data-testid="project-meta-badges">
      {region && (
        <Badge variant="secondary" data-testid="project-region-badge">
          {region}
        </Badge>
      )}
      {tenancyMode && (
        <Badge variant="outline" data-testid="project-tenancy-badge">
          {tenancyMode === 'single' ? 'Single-tenant' : tenancyMode === 'multi' ? 'Multi-tenant' : tenancyMode}
        </Badge>
      )}
    </div>
  )
}
