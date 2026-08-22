import { Navigate, Route } from 'react-router';
import DashboardPage from '@/pages/DashboardPage';
import AccountsPage from '@/pages/AccountsPage';
import UsersPage from '@/pages/UsersPage';
import InvitationsPage from '@/pages/InvitationsPage';
import GroupsPage from '@/pages/GroupsPage';
import CollectionsWorkspaceLayout from '@/pages/collections/CollectionsWorkspaceLayout';
import CollectionEmptyState from '@/pages/collections/CollectionEmptyState';
import CollectionNewPage from '@/pages/collections/CollectionNewPage';
import CollectionDetailLayout from '@/pages/collections/CollectionDetailLayout';
import CollectionDefaultTabRedirect from '@/pages/collections/CollectionDefaultTabRedirect';
import LegacyRecordsRedirect from '@/pages/collections/LegacyRecordsRedirect';
import SchemaTabPage from '@/pages/collections/tabs/SchemaTabPage';
import DataTabPage from '@/pages/collections/tabs/DataTabPage';
import RulesTabPage from '@/pages/collections/tabs/RulesTabPage';
import AnalyticsTabPage from '@/pages/collections/tabs/AnalyticsTabPage';
import RolesPage from '@/pages/RolesPage';
import AuditLogsPage from '@/pages/AuditLogsPage';
import MigrationsPage from '@/pages/MigrationsPage';
import MacrosPage from '@/pages/MacrosPage';
import CodelistsPage from '@/pages/codelists/CodelistsPage';
import ConfigurationDashboardPage from '@/pages/ConfigurationDashboardPage';
import ApiKeysPage from '@/pages/ApiKeys/ApiKeysPage';
import WebhooksPage from '@/pages/Webhooks/WebhooksPage';
import JobsPage from '@/pages/Jobs/JobsPage';
import ScheduledTasksPage from '@/pages/ScheduledTasks/ScheduledTasksPage';
import HooksPage from '@/pages/Hooks/HooksPage';
import HookEditorPage from '@/pages/Hooks/editor/HookEditorPage';
import HookOverviewPage from '@/pages/Hooks/HookOverviewPage';
import EndpointsPage from '@/pages/Endpoints/EndpointsPage';
import FunctionsPage from '@/pages/Functions/FunctionsPage';
import FunctionEditorPage from '@/pages/Functions/FunctionEditorPage';
import FunctionSecretsPage from '@/pages/Functions/FunctionSecretsPage';
import WorkflowsPage from '@/pages/Workflows/WorkflowsPage';
import WorkflowEditorPage from '@/pages/Workflows/editor/WorkflowEditorPage';
import WorkflowOverviewPage from '@/pages/Workflows/WorkflowOverviewPage';
import WorkflowRunDetailPage from '@/pages/Workflows/WorkflowRunDetailPage';
import AdminLayout from '@/layouts/AdminLayout';
import { IS_PLATFORM } from '@/lib/config';

/** Shared Studio child routes (relative to /admin or /project/:ref). */
export function StudioChildRoutes() {
  return studioChildRouteElements();
}

/** Route elements for nesting under a parent `<Route>` — call as `{studioChildRouteElements()}`, not `<… />`. */
export function studioChildRouteElements() {
  return (
    <>
      <Route index element={<Navigate to="dashboard" replace />} />
      <Route path="dashboard" element={<DashboardPage />} />
      {!IS_PLATFORM && <Route path="accounts" element={<AccountsPage />} />}
      {IS_PLATFORM && <Route path="accounts" element={<Navigate to="dashboard" replace />} />}
      <Route path="users" element={<UsersPage />} />
      <Route path="invitations" element={<InvitationsPage />} />
      <Route path="groups" element={<GroupsPage />} />
      <Route path="collections" element={<CollectionsWorkspaceLayout />}>
        <Route index element={<CollectionEmptyState />} />
        <Route path="new" element={<CollectionNewPage />} />
        <Route path=":collectionName" element={<CollectionDetailLayout />}>
          <Route index element={<CollectionDefaultTabRedirect />} />
          <Route path="schema" element={<SchemaTabPage />} />
          <Route path="data" element={<DataTabPage />} />
          <Route path="rules" element={<RulesTabPage />} />
          <Route path="analytics" element={<AnalyticsTabPage />} />
          <Route path="records" element={<LegacyRecordsRedirect />} />
        </Route>
      </Route>
      <Route path="roles" element={<RolesPage />} />
      <Route path="audit-logs" element={<AuditLogsPage />} />
      <Route path="migrations" element={<MigrationsPage />} />
      <Route path="macros" element={<MacrosPage />} />
      <Route path="codelists" element={<CodelistsPage />} />
      <Route path="codelists/:code" element={<CodelistsPage />} />
      <Route path="configuration" element={<ConfigurationDashboardPage />} />
      <Route path="api-keys" element={<ApiKeysPage />} />
      <Route path="webhooks" element={<WebhooksPage />} />
      <Route path="jobs" element={<JobsPage />} />
      <Route path="scheduled-tasks" element={<ScheduledTasksPage />} />
      <Route path="hooks" element={<HooksPage />} />
      <Route path="hooks/new" element={<HookEditorPage />} />
      <Route path="hooks/:id/edit" element={<HookEditorPage />} />
      <Route path="hooks/:id" element={<HookOverviewPage />} />
      <Route path="endpoints" element={<EndpointsPage />} />
      <Route path="functions" element={<FunctionsPage />} />
      <Route path="functions/secrets" element={<FunctionSecretsPage />} />
      <Route path="functions/:slug" element={<FunctionEditorPage />} />
      <Route path="workflows" element={<WorkflowsPage />} />
      <Route path="workflows/new" element={<WorkflowEditorPage />} />
      <Route path="workflows/:id/edit" element={<WorkflowEditorPage />} />
      <Route path="workflows/:id/runs/:instanceId" element={<WorkflowRunDetailPage />} />
      <Route path="workflows/:id" element={<WorkflowOverviewPage />} />
    </>
  );
}

export { AdminLayout };
