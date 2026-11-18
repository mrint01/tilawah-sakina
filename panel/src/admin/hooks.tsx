import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { BookOpen, CircleDot } from 'lucide-react';
import { api, type Action, type Kind, type PanelState, type Reel, type Status } from './api';
import { useToast } from './toast';
import { Badge } from './ui';

export const useAppState = () => useQuery({ queryKey: ['state'], queryFn: api.state, refetchInterval: 30_000 });
export const useInstagram = (enabled = true) =>
  useQuery({ queryKey: ['instagram'], queryFn: api.instagram, staleTime: 5 * 60_000, enabled });

/** Runs a panel action, shows a toast, and refreshes the state (GitHub needs a moment to reflect commits). */
export function useAct(success?: string | ((a: Action) => string)) {
  const qc = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: (a: Action) => api.act(a),
    onMutate: async (a) => {
      // Optimistic: status changes and the ON/OFF switch show at once.
      const prev = qc.getQueryData<PanelState>(['state']);
      if (!prev) return { prev };
      const next = structuredClone(prev);
      if (a.type === 'approve' || a.type === 'reject' || a.type === 'requeue') {
        const it = next.items.find((i) => i.id === a.id);
        if (it) {
          it.status = a.type === 'approve' ? 'approved' : a.type === 'reject' ? 'rejected' : 'pending';
          it.review = a.type === 'requeue' ? null : (a.note ?? it.review);
        }
      }
      if (a.type === 'toggle') next.config.enabled = a.enabled;
      if (a.type === 'mark_posted') {
        const it = next.items.find((i) => i.id === a.id);
        if (it) { it.status = 'posted'; it.posted = new Date().toISOString(); it.manual = true; if (a.permalink) it.permalink = a.permalink; }
      }
      qc.setQueryData(['state'], next);
      return { prev };
    },
    onError: (e: Error, _a, ctx) => {
      if (ctx?.prev) qc.setQueryData(['state'], ctx.prev);
      toast.show(e.message, { tone: 'error' });
    },
    onSuccess: (_d, a) => {
      if (success) toast.show(typeof success === 'function' ? success(a) : success, { tone: 'success' });
      setTimeout(() => void qc.invalidateQueries({ queryKey: ['state'] }), 2500);
    },
  });
}

export const KIND: Record<Kind, { label: string; tone: 'green' | 'violet'; icon: typeof BookOpen }> = {
  ayah: { label: 'Ayah', tone: 'green', icon: BookOpen },
  tasbih: { label: 'Tasbih', tone: 'violet', icon: CircleDot },
};

export function KindBadge({ kind }: { kind: Kind }) {
  const k = KIND[kind];
  return <Badge tone={k.tone}><k.icon className="h-3 w-3" aria-hidden="true" /> {k.label}</Badge>;
}

export const STATUS: Record<Status, { label: string; tone: 'orange' | 'green' | 'red' | 'blue' | 'slate' }> = {
  pending: { label: 'Needs review', tone: 'orange' },
  approved: { label: 'Approved', tone: 'green' },
  rejected: { label: 'Rejected', tone: 'red' },
  posted: { label: 'Posted', tone: 'blue' },
  failed: { label: 'Post failed', tone: 'red' },
};

export function StatusBadge({ status }: { status: Status }) {
  return <Badge tone={STATUS[status].tone}>{STATUS[status].label}</Badge>;
}

/** First frame of the contact sheet as a 9:16 thumbnail. */
export function Thumb({ state, reel, className = 'h-16 w-9' }: { state: PanelState; reel: Reel; className?: string }) {
  return (
    <span className={`block shrink-0 overflow-hidden rounded-md border border-paper-line bg-paper-alt bg-no-repeat ${className}`}
      style={{ backgroundImage: `url(${state.assets}${reel.id}.png)`, backgroundSize: 'auto 100%', backgroundPosition: 'left center' }}
      aria-hidden="true" />
  );
}

export const allChecksOk = (r: Reel) => Object.values(r.checks ?? {}).every(Boolean);
