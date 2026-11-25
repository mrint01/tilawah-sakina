import { StrictMode, useState, type FormEvent } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { MutationCache, QueryCache, QueryClient, QueryClientProvider, useQuery, useQueryClient } from '@tanstack/react-query';
import { KeyRound, Loader2 } from 'lucide-react';
import { AdminLayout, LogoMark } from './admin/AdminLayout';
import { api, notPosted, SignedOut } from './admin/api';
import { ToastProvider } from './admin/toast';
import { INPUT } from './admin/ui';
import OverviewPage from './pages/OverviewPage';
import AnalyticsPage from './pages/AnalyticsPage';
import ReviewPage from './pages/ReviewPage';
import QueuePage from './pages/QueuePage';
import PostedPage from './pages/PostedPage';
import NotPostedPage from './pages/NotPostedPage';
import RunsPage from './pages/RunsPage';
import SettingsPage from './pages/SettingsPage';
import './index.css';

const qc: QueryClient = new QueryClient({
  defaultOptions: { queries: { retry: (n, e) => !(e instanceof SignedOut) && n < 2, staleTime: 10_000 } },
  queryCache: new QueryCache({ onError: (e) => { if (e instanceof SignedOut) qc.setQueryData(['session'], false); } }),
  mutationCache: new MutationCache({ onError: (e) => { if (e instanceof SignedOut) qc.setQueryData(['session'], false); } }),
});

function Login() {
  const client = useQueryClient();
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await api.login(password);
      client.setQueryData(['session'], true);
      void client.invalidateQueries({ queryKey: ['state'] });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="flex min-h-screen items-center justify-center bg-paper-alt p-4">
      <form onSubmit={submit} className="flex w-full max-w-sm flex-col gap-4 rounded-2xl border border-paper-line bg-paper p-6 shadow-sm">
        <div className="flex items-center gap-3">
          <LogoMark className="!h-10 !w-10 !rounded-xl" />
          <div className="leading-tight">
            <p className="text-sm font-semibold">Reel Studio</p>
            <p className="text-xs uppercase tracking-[0.13em] text-ink-mute">Console</p>
          </div>
        </div>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-semibold uppercase tracking-wide text-ink-mute">Password</span>
          <input type="password" autoFocus autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} className={INPUT} />
        </label>
        {error && <p role="alert" className="rounded-lg bg-danger-light p-2.5 text-sm text-danger">{error}</p>}
        <button type="submit" disabled={busy || !password}
          className="flex h-10 cursor-pointer items-center justify-center gap-2 rounded-lg bg-accent text-sm font-semibold text-white hover:bg-accent-dark disabled:cursor-default disabled:opacity-50">
          {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <KeyRound className="h-4 w-4" aria-hidden="true" />} Sign in
        </button>
      </form>
    </div>
  );
}

function Console() {
  const client = useQueryClient();
  const location = useLocation();
  const session = useQuery({ queryKey: ['session'], queryFn: () => true, initialData: true, staleTime: Infinity });
  const state = useQuery({ queryKey: ['state'], queryFn: api.state, refetchInterval: 30_000, enabled: session.data });

  if (!session.data) return <Login />;
  const items = state.data?.items ?? [];
  const badges = {
    review: items.filter((i) => i.status === 'pending').length,
    queue: items.filter((i) => i.status === 'approved').length,
    missed: state.data ? notPosted(state.data).length : 0,
    // workflows whose latest finished run failed (a failure fixed by a later successful run no longer counts)
    failed: (() => {
      const latest = new Map<string, string | null>();
      for (const r of state.data?.runs ?? []) if (r.status === 'completed' && !latest.has(r.name)) latest.set(r.name, r.conclusion);
      return [...latest.values()].filter((c) => c === 'failure').length;
    })(),
  };
  const signOut = async () => {
    await api.logout().catch(() => {});
    client.setQueryData(['session'], false);
  };

  return (
    <AdminLayout name={state.data?.panel.name || 'Admin'} onSignOut={signOut} badges={badges}>
      <Routes location={location}>
        <Route path="/" element={<OverviewPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/review" element={<ReviewPage />} />
        <Route path="/queue" element={<QueuePage />} />
        <Route path="/posted" element={<PostedPage />} />
        <Route path="/not-posted" element={<NotPostedPage />} />
        <Route path="/runs" element={<RunsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AdminLayout>
  );
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={qc}>
      <ToastProvider>
        <BrowserRouter>
          <Console />
        </BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>
  </StrictMode>,
);
