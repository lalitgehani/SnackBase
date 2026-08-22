import './App.css';
import { Suspense, lazy } from 'react';
import { IS_PLATFORM } from '@/lib/config';
import { Loader2 } from 'lucide-react';

const SelfHostRoutes = lazy(() => import('@/routes/selfHost'));
const PlatformRoutes = lazy(() => import('@/routes/platform'));

function RouteFallback() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <Loader2 className="size-8 animate-spin text-primary" aria-hidden />
    </div>
  );
}

function App() {
  return (
    <Suspense fallback={<RouteFallback />}>
      {IS_PLATFORM ? <PlatformRoutes /> : <SelfHostRoutes />}
    </Suspense>
  );
}

export default App;
