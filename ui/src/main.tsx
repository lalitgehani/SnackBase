import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from '@/components/theme-provider';
import { RootProviders } from '@/RootProviders';
import './index.css';
import App from './App.tsx';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

createRoot(document.getElementById('root')!).render(
  <QueryClientProvider client={queryClient}>
    <ThemeProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      storageKey="snackbase.theme"
      disableTransitionOnChange
    >
      <RootProviders>
        <BrowserRouter basename="/_/">
          <App />
        </BrowserRouter>
      </RootProviders>
    </ThemeProvider>
  </QueryClientProvider>,
);
