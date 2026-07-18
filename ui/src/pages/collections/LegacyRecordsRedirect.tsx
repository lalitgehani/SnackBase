/**
 * Legacy URL compatibility: /records → /data
 */

import { Navigate, useParams } from 'react-router';

export default function LegacyRecordsRedirect() {
  const { collectionName } = useParams<{ collectionName: string }>();
  if (!collectionName) {
    return <Navigate to="/admin/collections" replace />;
  }
  return (
    <Navigate
      to={`/admin/collections/${collectionName}/data`}
      replace
    />
  );
}
