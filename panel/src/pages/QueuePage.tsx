import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { CalendarClock, Hand, Play, RotateCcw, Send, Trash2 } from 'lucide-react';
import { slotText, upcoming, type Reel, type Upcoming } from '../admin/api';
import { KIND, KindBadge, postingRun, Thumb, useAct, useAppState } from '../admin/hooks';
import { PublishProgress } from '../admin/PublishProgress';
import { NotPostedBar } from '../admin/NotPostedBar';
import { matchFilters, ReelFilterBar, useReelFilters } from '../admin/ReelFilters';
import { WeeklySection } from '../admin/WeeklySection';
import { ChangeTime } from '../admin/ChangeTime';
import { ago, Badge, dateTime, Empty, Modal, PageHeader, Pager, Skeleton, usePaged } from '../admin/ui';

/** The coming posting slots (5 a day) and the approved reel each one posts; empty slots show what is missing. */
export default function QueuePage() {
  const navigate = useNavigate();
  const state = useAppState();
  const act = useAct((a) => (a.type === 'post_now' ? 'Publishing started: follow it below' : a.type === 'reject' ? 'Removed: it will not be posted' : 'Moved back to review'));
  const [removing, setRemoving] = useState<Reel | null>(null);
  const [publishing, setPublishing] = useState<Reel | null>(null);
  const s = state.data;
  const busy = Boolean(s && postingRun(s));
  const approvedCount = s ? s.items.filter((i) => i.status === 'approved').length : 0;
  const plan: Upcoming[] = s ? upcoming(s.items, Math.max(10, approvedCount * 5 + 5), new Date(), s.slots) : [];
  // keep empty slots up to the last planned reel, plus the next 5 slots
  const lastFull = plan.map((p) => Boolean(p.reel)).lastIndexOf(true);
  const rows = plan.slice(0, Math.max(lastFull + 1, 5));
  const order = rows.filter((p) => p.reel).map((p) => p.reel as Reel);
  const [filters, setFilters] = useReelFilters();
  const filtering = filters.kind !== 'all' || filters.reciter || filters.surah;
  const shown = filtering ? rows.filter((p) => p.reel && matchFilters(p.reel, filters)) : rows;
  const paged = usePaged(shown, JSON.stringify(filters), 15);
  // only slots that come before the next 03:00 refill is checked are really skipped
  const missing = new Set(rows.filter((p) => !p.reel && p.at <= nextRefill().ready).map((p) => p.kind));

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Up next"
        text={s ? `${approvedCount} approved ${approvedCount === 1 ? 'reel' : 'reels'}, posted 5 a day: surah 00:00, dua 06:00, Asma al-Husna 12:00, tasbih 18:00, quiz 21:00.` : 'Loading…'}
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
      {s && <PublishProgress s={s} />}
      {s && <NotPostedBar s={s} />}
      {s && <WeeklySection s={s} />}
      {s && !s.config.enabled && <p className="rounded-xl bg-accent-light p-3 text-sm font-medium text-accent">Automation is OFF, so nothing posts until you turn it on in Overview.</p>}
      {s && s.config.enabled && missing.size > 0 && (
        <p className="rounded-xl bg-accent-light p-3 text-sm font-medium text-accent">
          Nothing approved yet for: {[...missing].map((k) => KIND[k].label).join(', ')}. Those slots are skipped; new reels are made at 03:00 and checked by Claude at 04:30.
        </p>
      )}

      <section className="overflow-hidden rounded-xl border border-paper-line bg-paper shadow-sm">
        {s && order.length > 0 && (
          <ReelFilterBar items={order} value={filters} onChange={setFilters} shown={shown.length} />
        )}
        {!s ? <div className="p-4"><Skeleton className="h-40" /></div> : rows.length === 0 ? (
          <Empty icon={CalendarClock} text="Nothing approved yet. New reels are made at 03:00 and checked by Claude at 04:30." />
        ) : shown.length === 0 ? (
          <Empty icon={CalendarClock} text="No approved reels match these filters." />
        ) : (
          <>
          {/* phones: one compact row per reel, text wraps instead of running off the screen */}
          <ul className="divide-y divide-paper-line sm:hidden">
            {paged.items?.map((p) => {
              const r = p.reel;
              if (!r) return <EmptySlot key={p.at.toISOString()} p={p} phone />;
              const i = order.indexOf(r);
              return (
                <li key={r.id} className="flex items-start">
                  <button type="button" onClick={() => navigate(`/review?reel=${r.id}`)} className="flex min-w-0 flex-1 cursor-pointer items-start gap-3 py-3 ps-4 text-start hover:bg-paper-alt">
                    <span className="num w-5 shrink-0 pt-0.5 text-xs text-ink-mute">{i + 1}</span>
                    <Thumb state={s} reel={r} className="h-14 w-8" />
                    <span className="min-w-0 flex-1">
                      <span className="line-clamp-2 text-sm font-semibold">{r.title}</span>
                      <span className="mt-0.5 line-clamp-1 text-xs text-ink-mute">{r.caption.split('\n')[0]}</span>
                      <span className="mt-1.5 flex flex-wrap items-center gap-2 text-xs text-ink-soft">
                        <KindBadge kind={r.kind} />
                        <span className="num">{r.duration}s</span>
                        <span>·</span>
                        {s.config.enabled ? <span className={i === 0 ? 'font-semibold text-ok' : ''}>{slotText(p)}</span> : <span className="text-ink-mute">paused</span>}
                      </span>
                    </span>
                  </button>
                  <button type="button" aria-label="Publish now" disabled={busy || !s.instagram} onClick={() => setPublishing(r)}
                    className="my-3 ms-2 inline-flex h-9 w-9 shrink-0 cursor-pointer items-center justify-center rounded-md bg-accent text-white hover:bg-accent-dark disabled:opacity-40">
                    <Send className="h-4 w-4" aria-hidden="true" />
                  </button>
                  <span className="my-3 ms-2 inline-flex"><ChangeTime r={r} next={p.at} small /></span>
                  <button type="button" aria-label="Remove, don't post" onClick={() => setRemoving(r)}
                    className="m-3 ms-2 inline-flex h-9 w-9 shrink-0 cursor-pointer items-center justify-center rounded-md border border-paper-line text-ink-soft hover:border-danger hover:text-danger">
                    <Trash2 className="h-4 w-4" aria-hidden="true" />
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
                {paged.items?.map((p) => {
                  const r = p.reel;
                  if (!r) return <EmptySlot key={p.at.toISOString()} p={p} />;
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
                      <td className="px-4 py-2.5">{s.config.enabled ? (i === 0 ? <Badge tone="green">{slotText(p)}</Badge> : slotText(p)) : <span className="text-ink-mute">paused</span>}</td>
                      <td className="whitespace-nowrap px-4 py-2.5">
                        <div className="flex items-center justify-end gap-2">
                        <button type="button" disabled={busy || !s.instagram} title={busy ? 'A post is already being published' : 'Publish this reel on Instagram now'}
                          onClick={(e) => { e.stopPropagation(); setPublishing(r); }}
                          className="inline-flex h-8 cursor-pointer items-center gap-1.5 rounded-md bg-accent px-2.5 text-xs font-semibold text-white hover:bg-accent-dark disabled:cursor-default disabled:opacity-40">
                          <Send className="h-3.5 w-3.5" aria-hidden="true" /> Publish now
                        </button>
                        <ChangeTime r={r} next={p.at} small />
                        <button type="button" aria-label="Back to review" title="Back to review" disabled={act.isPending}
                          onClick={(e) => { e.stopPropagation(); act.mutate({ type: 'requeue', id: r.id }); }}
                          className="inline-flex h-8 w-8 cursor-pointer items-center justify-center rounded-md border border-paper-line text-ink-soft hover:border-accent hover:text-accent">
                          <RotateCcw className="h-4 w-4" aria-hidden="true" />
                        </button>
                        <button type="button" aria-label="Remove, don't post" title="Remove, don't post" disabled={act.isPending}
                          onClick={(e) => { e.stopPropagation(); setRemoving(r); }}
                          className="inline-flex h-8 w-8 cursor-pointer items-center justify-center rounded-md border border-paper-line text-ink-soft hover:border-danger hover:text-danger">
                          <Trash2 className="h-4 w-4" aria-hidden="true" />
                        </button>
                        </div>
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

      <Modal open={Boolean(publishing)} onClose={() => setPublishing(null)} title="Publish this reel now?" icon={Send}
        text="It goes to Instagram right away with its caption. Follow the progress on this page until it is live.">
        <p className="text-sm font-semibold">{publishing?.title}</p>
        <p className="max-h-40 overflow-y-auto whitespace-pre-wrap rounded-lg border border-paper-line bg-paper-alt p-3 text-xs text-ink-soft">{publishing?.caption}</p>
        <div className="flex justify-end gap-2 pt-1">
          <button type="button" autoFocus onClick={() => setPublishing(null)}
            className="h-10 cursor-pointer rounded-lg border border-paper-line px-4 text-sm font-medium text-ink-soft hover:bg-paper-alt">Cancel</button>
          <button type="button" disabled={act.isPending || busy}
            onClick={() => { if (publishing) act.mutate({ type: 'post_now', id: publishing.id }, { onSuccess: () => { setPublishing(null); window.scrollTo({ top: 0, behavior: 'smooth' }); } }); }}
            className="flex h-10 cursor-pointer items-center gap-2 rounded-lg bg-accent px-4 text-sm font-semibold text-white hover:bg-accent-dark disabled:opacity-50">
            <Send className="h-4 w-4" aria-hidden="true" /> Publish now
          </button>
        </div>
      </Modal>

      <Modal open={Boolean(removing)} onClose={() => setRemoving(null)} title="Remove this reel?" icon={Trash2} tone="danger"
        text="It will not be posted. Its video file is deleted from GitHub at the next posting run; the next approved reel of the same type takes its slot. A new one is made at 03:00.">
        <p className="text-sm font-semibold">{removing?.title}</p>
        <div className="flex justify-end gap-2 pt-1">
          <button type="button" autoFocus onClick={() => setRemoving(null)}
            className="h-10 cursor-pointer rounded-lg border border-paper-line px-4 text-sm font-medium text-ink-soft hover:bg-paper-alt">Cancel</button>
          <button type="button" disabled={act.isPending}
            onClick={() => { if (removing) act.mutate({ type: 'reject', id: removing.id, note: 'Removed from Up next in the panel' }, { onSuccess: () => setRemoving(null) }); }}
            className="flex h-10 cursor-pointer items-center gap-2 rounded-lg bg-danger px-4 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50">
            <Trash2 className="h-4 w-4" aria-hidden="true" /> Remove
          </button>
        </div>
      </Modal>
    </div>
  );
}

/** A posting slot with nothing approved of its kind: shown so the gap is visible. */
/** The next 03:00 refill (Tunisia, 02:00 UTC) and when its reels are checked (04:30). */
function nextRefill(now = new Date()) {
  const t = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), 2));
  if (t <= now) t.setUTCDate(t.getUTCDate() + 1);
  return { at: t, ready: new Date(t.getTime() + 90 * 60_000) };
}
const refillDay = new Intl.DateTimeFormat('en-GB', { weekday: 'short', day: 'numeric', month: 'short', timeZone: 'Africa/Tunis' });

function EmptySlot({ p, phone }: { p: Upcoming; phone?: boolean }) {
  const r = nextRefill();
  const text = p.at > r.ready
    ? `Not made yet: the ${KIND[p.kind].label.toLowerCase()} for this slot is made at 03:00 on ${refillDay.format(r.at)}`
    : `Nothing approved: this ${KIND[p.kind].label.toLowerCase()} slot is skipped`;
  if (phone) {
    return (
      <li className="flex items-center gap-3 px-4 py-3 text-sm text-ink-mute">
        <KindBadge kind={p.kind} /> <span className="flex-1">{text}</span> <span className="text-xs">{slotText(p)}</span>
      </li>
    );
  }
  return (
    <tr className="text-ink-mute">
      <td className="px-4 py-2.5">–</td>
      <td className="px-4 py-2.5 italic">{text}</td>
      <td className="px-4 py-2.5"><KindBadge kind={p.kind} /></td>
      <td className="px-4 py-2.5" /><td className="px-4 py-2.5" />
      <td className="px-4 py-2.5">{slotText(p)}</td>
      <td className="px-4 py-2.5" />
    </tr>
  );
}
