/**
 * Analytics tab — embeds AnalyticsPage in workspace shell.
 */

import AnalyticsPage from '@/pages/AnalyticsPage';

export default function AnalyticsTabPage() {
  return (
    <div data-testid="analytics-tab">
      <AnalyticsPage embedded />
    </div>
  );
}
