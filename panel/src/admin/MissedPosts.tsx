import { CalendarX2, RotateCw } from 'lucide-react';
import type { PanelState } from './api';
import { KindBadge } from './hooks';
import { Badge } from './ui';

const when = new Intl.DateTimeFormat('en-GB', { weekday: 'short', day: 'numeric', month: 'short' });

/**
 * Posting slots of the last 7 days that did not go out, with the reason (from the slot log in queue.json), and slots
 * being retried right now. The reel itself is not lost: it stays approved and goes out at the next slot of its type.
 */
export function MissedPosts({ s, compact = false }: { s: PanelState; compact?: boolean }) {
  const cut = new Date(Date.now() - 7 * 86400_000 + 3600_000).toISOString().slice(0, 10);
  const rows = Object.entries(s.slots ?? {})
    .filter(([k, e]) => k >= cut && (e.status === 'missed' || e.status === 'failed'))
    .sort(([a], [b]) => b.localeCompare(a));
  const late = Object.entries(s.slots ?? {}).filter(([k, e]) => k >= cut && e.status === 'posted' && (e.late_min ?? 0) >= 20);
  if (!rows.length) return null;
  return (
    <section className="rounded-xl border border-danger/40 bg-paper p-4 shadow-sm" aria-label="Missed posts">
      <div className="mb-2 flex items-center gap-2">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-danger-light text-danger"><CalendarX2 className="h-4 w-4" aria-hidden="true" /></span>
        <div className="min-w-0 flex-1">
          <h2 className="text-sm font-semibold">Not posted ({rows.length} in the last 7 days)</h2>
          <p className="text-xs text-ink-mute">The reel is not lost: it stays approved and goes out at the next slot of its type.{late.length ? ` ${late.length} other ${late.length === 1 ? 'post was' : 'posts were'} late but went out.` : ''}</p>
        </div>
      </div>
      <ul className="divide-y divide-paper-line">
        {rows.slice(0, compact ? 3 : 14).map(([k, e]) => {
          const [day, time] = k.split(' ');
          return (
            <li key={k} className="flex flex-wrap items-start gap-x-3 gap-y-1 py-2 text-sm">
              <span className="num w-32 shrink-0 text-xs text-ink-soft">{when.format(new Date(`${day}T12:00:00Z`))} · {time}</span>
              <KindBadge kind={e.kind} />
              {e.status === 'failed'
                ? <Badge tone="orange"><RotateCw className="h-3 w-3" aria-hidden="true" /> Failed, trying again</Badge>
                : <Badge tone="red">Not posted</Badge>}
              <span className="min-w-0 basis-full text-xs text-ink-mute sm:basis-auto sm:flex-1">
                {e.reason || 'Unknown reason'}{e.tries ? ` · ${e.tries} ${e.tries === 1 ? 'try' : 'tries'}` : ''}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
