import './App.css';
import { Suspense, lazy } from 'react';
import { IS_PLATFORM } from '@/lib/config';
import { Loader2 } from 'lucide-react';

const AppRoutes = lazy(() =>
  IS_PLATFORM ? import('@/routes/platform') : import('@/routes/selfHost'),
);

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
      <AppRoutes />
    </Suspense>
  );
}

export default App;
