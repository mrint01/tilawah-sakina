import { useNavigate } from 'react-router-dom';
import { CalendarClock, Hand, Play, RotateCcw } from 'lucide-react';
import { nextSlots, postingOrder, slot } from '../admin/api';
import { KindBadge, Thumb, useAct, useAppState } from '../admin/hooks';
import { matchFilters, ReelFilterBar, useReelFilters } from '../admin/ReelFilters';
import { ago, Badge, dateTime, Empty, PageHeader, Pager, Skeleton, usePaged } from '../admin/ui';

/** Approved reels in the order the workflow will post them, with their expected time slot. */
export default function QueuePage() {
  const navigate = useNavigate();
  const state = useAppState();
  const act = useAct((a) => (a.type === 'post_now' ? 'Posting started, watch Workflow runs' : 'Moved back to review'));
  const s = state.data;
  const order = s ? postingOrder(s.items, s.config.alternate) : [];
  const slots = nextSlots(order.length);
  // filters only change what is shown: the posting order and the # numbers stay the same
  const [filters, setFilters] = useReelFilters();
  const shown = order.filter((r) => matchFilters(r, filters));
  const paged = usePaged(shown, JSON.stringify(filters), 15);

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Up next"
        text={s ? `${order.length} approved ${order.length === 1 ? 'reel' : 'reels'}: about ${Math.floor(order.length / 2)} ${Math.floor(order.length / 2) === 1 ? 'day' : 'days'} of posts at 2 a day.` : 'Loading…'}
        actions={
          <div className="flex flex-wrap gap-2">
          {s && !s.instagram && order[0] && (
            <button type="button" onClick={() => navigate(`/review?reel=${order[0].id}`)}
              className="flex h-10 cursor-pointer items-center gap-2 rounded-lg border border-accent px-3 text-sm font-semibold text-accent hover:bg-accent/10">
              <Hand className="h-4 w-4" aria-hidden="true" /> Post next by hand
            </button>
          )}
          <button type="button" disabled={!order.length || act.isPending || !s?.instagram} title={s?.instagram ? undefined : 'Connect Instagram first; until then use “Post next by hand”'} onClick={() => act.mutate({ type: 'post_now' })}
            className="flex h-10 cursor-pointer items-center gap-2 rounded-lg bg-accent px-3 text-sm font-semibold text-white hover:bg-accent-dark disabled:cursor-default disabled:opacity-50">
            <Play className="h-4 w-4" aria-hidden="true" /> Post next now
          </button>
          </div>
        }
      />
      {s && !s.config.enabled && <p className="rounded-xl bg-accent-light p-3 text-sm font-medium text-accent">Automation is OFF, so nothing posts until you turn it on in Overview.</p>}

      <section className="overflow-hidden rounded-xl border border-paper-line bg-paper shadow-sm">
        {s && order.length > 0 && (
          <ReelFilterBar items={order} value={filters} onChange={setFilters} shown={shown.length} />
        )}
        {!s ? <div className="p-4"><Skeleton className="h-40" /></div> : order.length === 0 ? (
          <Empty icon={CalendarClock} text="Nothing approved yet. Approve reels in Review to fill the schedule." />
        ) : shown.length === 0 ? (
          <Empty icon={CalendarClock} text="No approved reels match these filters." />
        ) : (
          <>
          {/* phones: one compact row per reel, text wraps instead of running off the screen */}
          <ul className="divide-y divide-paper-line sm:hidden">
            {paged.items?.map((r) => {
              const i = order.indexOf(r);
              return (
                <li key={r.id}>
                  <button type="button" onClick={() => navigate(`/review?reel=${r.id}`)} className="flex w-full cursor-pointer items-start gap-3 px-4 py-3 text-start hover:bg-paper-alt">
                    <span className="num w-5 shrink-0 pt-0.5 text-xs text-ink-mute">{i + 1}</span>
                    <Thumb state={s} reel={r} className="h-14 w-8" />
                    <span className="min-w-0 flex-1">
                      <span className="line-clamp-2 text-sm font-semibold">{r.title}</span>
                      <span className="mt-0.5 line-clamp-1 text-xs text-ink-mute">{r.caption.split('\n')[0]}</span>
                      <span className="mt-1.5 flex flex-wrap items-center gap-2 text-xs text-ink-soft">
                        <KindBadge kind={r.kind} />
                        <span className="num">{r.duration}s</span>
                        <span>·</span>
                        {s.config.enabled ? <span className={i === 0 ? 'font-semibold text-ok' : ''}>{slot(slots[i])}</span> : <span className="text-ink-mute">paused</span>}
                      </span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
          <div className="hidden overflow-x-auto sm:block">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-paper-line text-left text-xs uppercase text-ink-mute">
                  <th className="px-4 py-2.5 font-semibold">#</th>
                  <th className="px-4 py-2.5 font-semibold">Reel</th>
                  <th className="px-4 py-2.5 font-semibold">Type</th>
                  <th className="px-4 py-2.5 text-right font-semibold">Length</th>
                  <th className="px-4 py-2.5 font-semibold">Approved</th>
                  <th className="px-4 py-2.5 font-semibold">Goes out</th>
                  <th className="px-4 py-2.5" />
                </tr>
              </thead>
              <tbody className="divide-y divide-paper-line">
                {paged.items?.map((r) => {
                  const i = order.indexOf(r);
                  return (
                    <tr key={r.id} onClick={() => navigate(`/review?reel=${r.id}`)} className="cursor-pointer hover:bg-paper-alt">
                      <td className="num px-4 py-2.5 text-ink-mute">{i + 1}</td>
                      <td className="px-4 py-2.5">
                        <span className="flex items-center gap-3">
                          <Thumb state={s} reel={r} className="h-12 w-[27px]" />
                          <span className="min-w-0">
                            <span className="block truncate font-semibold">{r.title}</span>
                            <span className="block truncate text-xs text-ink-mute">{r.caption.split('\n')[0]}</span>
                          </span>
                        </span>
                      </td>
                      <td className="px-4 py-2.5"><KindBadge kind={r.kind} /></td>
                      <td className="num px-4 py-2.5 text-right">{r.duration}s</td>
                      <td className="px-4 py-2.5 text-ink-soft" title={dateTime(r.reviewed ?? null)}>{ago(r.reviewed ?? null)}</td>
                      <td className="px-4 py-2.5">{s.config.enabled ? (i === 0 ? <Badge tone="green">{slot(slots[i])}</Badge> : slot(slots[i])) : <span className="text-ink-mute">paused</span>}</td>
                      <td className="px-4 py-2.5 text-right">
                        <button type="button" aria-label="Back to review" title="Back to review" disabled={act.isPending}
                          onClick={(e) => { e.stopPropagation(); act.mutate({ type: 'requeue', id: r.id }); }}
                          className="inline-flex h-8 w-8 cursor-pointer items-center justify-center rounded-md border border-paper-line text-ink-soft hover:border-accent hover:text-accent">
                          <RotateCcw className="h-4 w-4" aria-hidden="true" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          </>
        )}
        <Pager paged={paged} className="border-t border-paper-line px-4 py-3" />
      </section>
    </div>
  );
}
