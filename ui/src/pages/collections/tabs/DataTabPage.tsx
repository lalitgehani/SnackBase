/**
 * Data tab — embeds RecordsPage in workspace shell.
 */

import RecordsPage from '@/pages/RecordsPage';

export default function DataTabPage() {
  return (
    <div data-testid="data-tab">
      <RecordsPage embedded />
    </div>
  );
}
