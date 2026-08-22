import { useQuery } from '@tanstack/react-query'
import { useSnackBase } from '@snackbase/react'
import { ChevronsUpDown, Building2, Check } from 'lucide-react'
import { useNavigate } from 'react-router'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from '@/components/ui/sidebar'
import { useOrgContextStore, type ActiveOrg } from '@/stores/org-context.store'
import type { Organization } from '@/types/control-plane'

export function OrgSwitcher() {
  const client = useSnackBase()
  const navigate = useNavigate()
  const { isMobile } = useSidebar()
  const { activeOrg, setActiveOrg } = useOrgContextStore()

  const { data: orgs = [], isLoading } = useQuery({
    queryKey: ['organizations'],
    queryFn: async () => {
      const res = await client.records.list<Organization>('organizations', {
        sort: 'name',
        limit: 100,
      })
      return res.items
    },
  })

  const selectOrg = (org: ActiveOrg) => {
    setActiveOrg(org)
    navigate(`/organizations/${org.id}/projects`)
  }

  const label = activeOrg?.name ?? (isLoading ? 'Loading…' : 'Select organization')

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <SidebarMenuButton
              size="lg"
              className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
              data-testid="org-switcher"
            >
              <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
                <Building2 className="size-4" />
              </div>
              <div className="grid flex-1 text-left text-sm leading-tight">
                <span className="truncate font-semibold">{label}</span>
                <span className="truncate text-xs text-muted-foreground">
                  {activeOrg?.slug ?? 'Organization'}
                </span>
              </div>
              <ChevronsUpDown className="ml-auto size-4" />
            </SidebarMenuButton>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            className="w-[--radix-dropdown-menu-trigger-width] min-w-56 rounded-lg"
            align="start"
            side={isMobile ? 'bottom' : 'right'}
            sideOffset={4}
          >
            <DropdownMenuLabel className="text-xs text-muted-foreground">
              Organizations
            </DropdownMenuLabel>
            {orgs.length === 0 && !isLoading && (
              <DropdownMenuItem disabled>No organizations yet</DropdownMenuItem>
            )}
            {orgs.map((org) => (
              <DropdownMenuItem
                key={org.id}
                onClick={() =>
                  selectOrg({ id: org.id, name: org.name, slug: org.slug })
                }
                className="gap-2 p-2"
              >
                <Building2 className="size-4 shrink-0" />
                <span className="truncate">{org.name}</span>
                {activeOrg?.id === org.id && (
                  <Check className="ml-auto size-4" />
                )}
              </DropdownMenuItem>
            ))}
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={() => navigate('/organizations/new')}
              data-testid="org-switcher-create"
            >
              Create organization
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => navigate('/organizations')}>
              View all organizations
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarMenuItem>
    </SidebarMenu>
  )
}
