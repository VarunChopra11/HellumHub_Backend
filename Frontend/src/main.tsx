import React from 'react';
import ReactDOM from 'react-dom/client';
import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { Toaster, toast } from 'sonner';
import App from '@/App';
import { getApiErrorMessage } from '@/lib/apiError';
import { TooltipProvider } from '@/components/ui';
import './index.css';

const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error) => {
      toast.error(getApiErrorMessage(error), { duration: 4000 });
    },
  }),
  mutationCache: new MutationCache({
    onError: (error) => {
      toast.error(getApiErrorMessage(error), { duration: 4000 });
    },
  }),
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 20000,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </TooltipProvider>
      <Toaster
        position="bottom-right"
        duration={4000}
        theme="dark"
        toastOptions={{
          className: '!bg-[var(--bg-card)] !border !border-[var(--border)] !text-[var(--text-primary)]',
        }}
      />
    </QueryClientProvider>
  </React.StrictMode>,
);
