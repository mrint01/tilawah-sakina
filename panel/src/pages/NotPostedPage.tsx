import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CalendarClock, CalendarX2, RotateCw, Send } from 'lucide-react';
import { notPosted, slotText, slotWhen, upcoming, type NotPosted } from '../admin/api';
import { KIND, KindBadge, postingRun, Thumb, useAct, useAppState } from '../admin/hooks';
import { PublishProgress } from '../admin/PublishProgress';
import { Badge, Empty, Modal, PageHeader, Skeleton } from '../admin/ui';

const when = slotWhen;

/**
 * Posting slots of the last 7 days that did not go out, with why, and a reel of the same type to publish for it now.
 * Publishing one fills that slot (it leaves this list); the reel's own later slot then posts the next reel.
 */
export default function NotPostedPage() {
  const navigate = useNavigate();
  const state = useAppState();
  const s = state.data;
  const act = useAct((a) => (a.type === 'slot_resolve' ? 'Kept in the schedule: it posts at its next slot' : 'Publishing started: follow it at the top of the page'));
  const [ask, setAsk] = useState<NotPosted | null>(null);
  const rows = s ? notPosted(s) : [];
  const busy = Boolean(s && postingRun(s));
  // when each approved reel goes out if nothing is done
  const plan = s ? upcoming(s.items, 40, new Date(), s.slots) : [];
  const nextFor = (id: string) => plan.find((p) => p.reel?.id === id);

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="Not posted"
        text="Slots of the last 7 days that did not go out, and why. Publish the reel now, or keep it in the schedule (it posts at the next slot of its type). Either way it leaves this list." />
      {s && <PublishProgress s={s} />}

      <section className="overflow-hidden rounded-xl border border-paper-line bg-paper shadow-sm">
        {!s ? <div className="p-4"><Skeleton className="h-40" /></div> : rows.length === 0 ? (
          <Empty icon={CalendarX2} text="Every slot of the last 7 days was posted." />
        ) : (
          <ul className="divide-y divide-paper-line">
            {rows.map((row) => {
              const { key, entry: e, reel: r } = row;
              return (
                <li key={key} className="flex flex-col gap-3 p-4 lg:flex-row lg:items-center">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="num text-sm font-semibold">{when(key)}</span>
                      <KindBadge kind={e.kind} />
                      {e.status === 'failed'
                        ? <Badge tone="orange"><RotateCw className="h-3 w-3" aria-hidden="true" /> Failed, trying again</Badge>
                        : <Badge tone="red">Not posted</Badge>}
                    </div>
                    <p className="mt-1 text-xs text-ink-mute">
                      {e.reason || 'Unknown reason'}{e.tries ? ` · ${e.tries} ${e.tries === 1 ? 'try' : 'tries'}` : ''}
                    </p>
                  </div>
                  {r ? (
                    <button type="button" onClick={() => navigate(`/review?reel=${r.id}`)}
                      className="flex min-w-0 cursor-pointer items-center gap-3 rounded-lg p-1 text-start hover:bg-paper-alt lg:w-72">
                      <Thumb state={s} reel={r} className="h-12 w-7" />
                      <span className="min-w-0">
                        <span className="block truncate text-sm font-medium">{r.title}</span>
                        <span className="text-xs text-ink-mute">{r.duration}s · {nextFor(r.id) ? `next: ${slotText(nextFor(r.id)!)}` : 'approved'}</span>
                      </span>
                    </button>
                  ) : (
                    <p className="text-xs text-ink-mute lg:w-72">No approved {KIND[e.kind].label.toLowerCase()} reel left to publish.</p>
                  )}
                  <div className="flex shrink-0 flex-wrap gap-2">
                  <button type="button" disabled={act.isPending || e.status === 'failed'}
                    title={r && nextFor(r.id) ? `It posts ${slotText(nextFor(r.id)!)}` : 'Let this slot go'}
                    onClick={() => act.mutate({ type: 'slot_resolve', slot: key })}
                    className="flex h-9 cursor-pointer items-center justify-center gap-2 rounded-lg border border-paper-line px-3 text-sm font-medium text-ink-soft hover:bg-paper-alt disabled:cursor-default disabled:opacity-40">
                    <CalendarClock className="h-4 w-4" aria-hidden="true" /> Keep in schedule
                  </button>
                  <button type="button" disabled={!r || busy || !s.instagram || act.isPending || e.status === 'failed'}
                    title={e.status === 'failed' ? 'The hourly run is still retrying this slot' : busy ? 'A post is already being published' : !s.instagram ? 'Connect Instagram first' : 'Publish this reel for the missed slot now'}
                    onClick={() => setAsk(row)}
                    className="flex h-9 shrink-0 cursor-pointer items-center justify-center gap-2 rounded-lg bg-accent px-3 text-sm font-semibold text-white hover:bg-accent-dark disabled:cursor-default disabled:opacity-40">
                    <Send className="h-4 w-4" aria-hidden="true" /> Publish now
                  </button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <Modal open={Boolean(ask)} onClose={() => setAsk(null)} title="Publish it now?" icon={Send}
        text={ask ? `For the ${when(ask.key)} ${KIND[ask.entry.kind].label.toLowerCase()} slot. It goes to Instagram right away with its caption and cover.` : ''}>
        {ask?.reel && <p className="text-sm font-semibold">{ask.reel.title}</p>}
        <div className="flex justify-end gap-2 pt-1">
          <button type="button" autoFocus onClick={() => setAsk(null)}
            className="h-10 cursor-pointer rounded-lg border border-paper-line px-4 text-sm font-medium text-ink-soft hover:bg-paper-alt">Cancel</button>
          <button type="button" disabled={act.isPending || busy || !ask?.reel}
            onClick={() => ask?.reel && act.mutate({ type: 'post_now', id: ask.reel.id, slot: ask.key },
              { onSuccess: () => { setAsk(null); window.scrollTo({ top: 0, behavior: 'smooth' }); } })}
            className="flex h-10 cursor-pointer items-center gap-2 rounded-lg bg-accent px-4 text-sm font-semibold text-white hover:bg-accent-dark disabled:opacity-50">
            <Send className="h-4 w-4" aria-hidden="true" /> Publish now
          </button>
        </div>
      </Modal>
    </div>
  );
}
