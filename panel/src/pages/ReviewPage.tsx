import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Check, CheckCircle2, ExternalLink, Inbox, MousePointerClick, RefreshCw, RotateCcw, Undo2, X, XCircle } from 'lucide-react';
import { cn } from '../admin/cn';
import { asset, CHECK_LABEL, type PanelState, type Reel } from '../admin/api';
import { ManualPost } from '../admin/ManualPost';
import { MakeProgressCard, MakeReelsButton } from '../admin/MakeReels';
import { allChecksOk, makingRun, KindBadge, StatusBadge, Thumb, useAct, useAppState, useInstagram } from '../admin/hooks';
import { InsightsNote, ReelStats } from '../admin/IgStats';
import { ago, Badge, dateTime, Empty, PageHeader, Pager, SELECT, Skeleton, usePaged } from '../admin/ui';

type Filter = 'pending' | 'rejected' | 'failed' | 'all';
const FILTERS: { value: Filter; label: string }[] = [
  { value: 'pending', label: 'Needs review' }, { value: 'rejected', label: 'Rejected' },
  { value: 'failed', label: 'Post failed' }, { value: 'all', label: 'All reels' },
];
const match = (r: Reel, f: Filter) => (f === 'all' ? true : r.status === f);

/** Every reel is checked here before it can be posted. The picked reel (?reel=id) is the main column, the list is on the right;
 *  on phones the picked reel comes first and the list under it. */
export default function ReviewPage() {
  const state = useAppState();
  const [params, setParams] = useSearchParams();
  // Opened from a link to one reel: show every status so that reel is in the list too.
  const [filter, setFilter] = useState<Filter>(() => (params.get('reel') ? 'all' : 'pending'));
  const list = [...(state.data?.items ?? [])].reverse();
  const shown = list.filter((r) => match(r, filter));
  const paged = usePaged(shown, filter);
  const selected = list.find((r) => r.id === params.get('reel')) ?? null;
  const count = (f: Filter) => list.filter((r) => match(r, f)).length;
  const open = (id: string) => {
    setParams({ reel: id }, { replace: true });
    // the picked reel is at the top: bring it into view once it has rendered
    requestAnimationFrame(() => document.getElementById('reel')?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
  };

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Review"
        text="Watch each reel before it goes out. Only approved reels are ever posted."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <select aria-label="Status" value={filter} onChange={(e) => setFilter(e.target.value as Filter)} className={SELECT}>
              {FILTERS.map((f) => <option key={f.value} value={f.value}>{f.label} ({count(f.value)})</option>)}
            </select>
            <MakeReelsButton busy={Boolean(makingRun(state.data))} reciters={Object.keys(state.data?.config.reciters ?? {})} />
            <button type="button" onClick={() => void state.refetch()}
              className="flex h-9 cursor-pointer items-center gap-2 rounded-lg border border-paper-line bg-paper px-3 text-sm font-medium hover:bg-paper-alt">
              <RefreshCw className={cn('h-4 w-4', state.isFetching && 'animate-spin')} aria-hidden="true" /> Refresh
            </button>
          </div>
        }
      />
      {state.data && <MakeProgressCard s={state.data} />}
      {state.error && <p className="rounded-xl bg-danger-light p-3 text-sm text-danger">{(state.error as Error).message}</p>}

      <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,24rem)]">
        {/* phones: the picked reel shows above the list; with nothing picked only the list shows */}
        {state.data && <ReelPanel s={state.data} r={selected} className={selected ? 'scroll-mt-16' : 'hidden lg:block'} />}
        <section className="flex flex-col rounded-xl border border-paper-line bg-paper shadow-sm lg:sticky lg:top-16 lg:max-h-[calc(100vh-5rem)]">
          <div className="border-b border-paper-line px-4 py-3">
            <h2 className="text-sm font-semibold">{selected ? 'Other reels' : 'Reels'}</h2>
            <p className="text-xs text-ink-mute">{state.data ? `${shown.length} shown` : 'Loading…'}</p>
          </div>
          {!state.data ? <div className="p-4"><Skeleton className="h-40" /></div> : shown.length === 0 ? (
            <Empty icon={Inbox} text={filter === 'pending' ? 'Nothing waiting. New reels arrive every morning, or press “Make reels”.' : 'Nothing here for this status.'} />
          ) : (
            <ul className="divide-y divide-paper-line lg:overflow-y-auto">
              {paged.items?.map((r) => <ReelRow key={r.id} s={state.data!} r={r} active={r.id === selected?.id} onOpen={() => open(r.id)} />)}
            </ul>
          )}
          <Pager paged={paged} className="border-t border-paper-line px-4 py-3" />
        </section>
      </div>
    </div>
  );
}

function ReelRow({ s, r, active, onOpen }: { s: PanelState; r: Reel; active: boolean; onOpen: () => void }) {
  const ok = allChecksOk(r);
  return (
    <li>
      <button type="button" onClick={onOpen} aria-current={active || undefined}
        className={cn('relative flex w-full cursor-pointer items-start gap-3 px-4 py-3 text-start transition-colors', active ? 'bg-accent/10' : 'hover:bg-paper-alt')}>
        {active && <span className="absolute inset-y-0 start-0 w-[3px] bg-accent" aria-hidden="true" />}
        <span className={cn('mt-1 h-2 w-2 shrink-0 rounded-full', r.status === 'pending' ? 'bg-accent' : 'bg-transparent')} aria-label={r.status === 'pending' ? 'Needs review' : undefined} />
        <Thumb state={s} reel={r} />
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-1.5">
            <KindBadge kind={r.kind} />
            <span className="truncate font-semibold">{r.title}</span>
            {r.status !== 'pending' && <StatusBadge status={r.status} />}
          </span>
          <span className="mt-1 line-clamp-2 block text-sm text-ink-soft">{r.caption.split('\n')[0]}</span>
          <span className={cn('mt-1 flex items-center gap-1 text-xs', ok ? 'text-ok' : 'text-danger')}>
            {ok ? <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" /> : <XCircle className="h-3.5 w-3.5" aria-hidden="true" />}
            {ok ? 'All checks passed' : 'Failed checks'} · {r.duration}s
          </span>
        </span>
        <span className="shrink-0 text-xs text-ink-mute" title={dateTime(r.created)}>{ago(r.created)}</span>
      </button>
    </li>
  );
}

function ReelPanel({ s, r, className = '' }: { s: PanelState; r: Reel | null; className?: string }) {
  const act = useAct((a) => (a.type === 'approve' ? 'Approved: it joins the posting schedule' : a.type === 'reject' ? 'Rejected: it will not be posted' : a.type === 'unmark_posted' ? 'Back in the posting schedule' : 'Moved back to review'));
  const [note, setNote] = useState('');
  useEffect(() => setNote(''), [r?.id]);
  const ig = useInstagram(Boolean(s.instagram));

  if (!r) {
    return (
      <section id="reel" className={`rounded-xl border border-paper-line bg-paper shadow-sm ${className}`}>
        <div className="border-b border-paper-line px-4 py-3">
          <h2 className="text-sm font-semibold">Pick a reel</h2>
          <p className="text-xs text-ink-mute">Select a reel in the list to watch it, see its numbers and checks, and approve or reject it.</p>
        </div>
        <p className="flex flex-col items-center gap-2 px-4 py-12 text-sm text-ink-mute"><MousePointerClick className="h-6 w-6" aria-hidden="true" /> Nothing selected.</p>
      </section>
    );
  }
  const ok = allChecksOk(r);
  const decided = r.status === 'approved' || r.status === 'rejected' || r.status === 'failed';
  const m = ig.data?.media?.[r.id];
  const link = r.permalink || m?.permalink;
  const hasVideo = r.status !== 'posted' || r.manual;
  return (
    <section id="reel" className={`rounded-xl border border-paper-line bg-paper shadow-sm ${className}`}>
      <div className="flex items-start gap-3 border-b border-paper-line px-4 py-3">
        <div className="min-w-0 flex-1">
          <h2 className="flex flex-wrap items-center gap-1.5 text-sm font-semibold"><KindBadge kind={r.kind} /> <span className="truncate">{r.title}</span></h2>
          <p className="mt-0.5 text-xs text-ink-mute">Made {dateTime(r.created)} · {ago(r.created)}</p>
        </div>
        <StatusBadge status={r.status} />
      </div>

      <div className="grid gap-4 p-4 xl:grid-cols-[minmax(0,20rem)_minmax(0,1fr)]">
        {/* left: the reel itself and its Instagram numbers */}
        <div className="flex flex-col items-center gap-3">
          {hasVideo ? (
            <video key={r.id} src={`/api/video?id=${encodeURIComponent(r.id)}#t=0.5`} controls playsInline preload="metadata"
              className="aspect-[9/16] max-h-[60vh] w-auto max-w-full rounded-lg border border-paper-line bg-black" />
          ) : m?.thumbnail ? (
            <a href={link} target="_blank" rel="noreferrer" className="block">
              <img src={m.thumbnail} alt="Cover of the reel on Instagram" className="aspect-[9/16] max-h-[60vh] w-auto rounded-lg border border-paper-line object-cover" />
            </a>
          ) : (
            <img src={asset(s, r.id, 'png')} alt="Six frames spread over the reel" loading="lazy" className="w-full rounded-lg border border-paper-line" />
          )}
          {link && (
            <a href={link} target="_blank" rel="noreferrer" className="flex items-center gap-1.5 text-sm font-medium text-accent hover:underline">
              <ExternalLink className="h-4 w-4" aria-hidden="true" /> Open on Instagram
            </a>
          )}
        </div>

        <div className="flex min-w-0 flex-col gap-4">
        {r.status === 'posted' && (
          <div className="flex flex-col gap-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-ink-mute">
              On Instagram{m?.timestamp ? ` · posted ${ago(m.timestamp)}` : ''}
            </p>
            {s.instagram ? <ReelStats m={m} /> : <p className="text-sm text-ink-mute">Connect Instagram to see views, likes and shares.</p>}
            {s.instagram && ig.data && !m && <p className="text-xs text-ink-mute">This reel isn't matched to a post on the account yet. Add its Instagram link to match it.</p>}
            {ig.data?.insights_error && <InsightsNote text={ig.data.insights_error} />}
          </div>
        )}
        {r.status === 'approved' && !s.instagram && <ManualPost reel={r} />}

        {r.status === 'posted' && r.manual && (
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-paper-line p-3">
            <p className="text-sm text-ink-soft">Marked as posted by hand {ago(r.posted ?? null)}.</p>
            <button type="button" disabled={act.isPending} onClick={() => act.mutate({ type: 'unmark_posted', id: r.id })}
              className="flex h-9 cursor-pointer items-center gap-2 rounded-lg border border-paper-line px-3 text-sm font-medium text-ink-soft hover:bg-paper-alt disabled:opacity-50">
              <Undo2 className="h-4 w-4" aria-hidden="true" /> Not posted (undo)
            </button>
          </div>
        )}

        {(hasVideo || m?.thumbnail) && <img src={asset(s, r.id, 'png')} alt="Six frames spread over the reel" loading="lazy" className="w-full rounded-lg border border-paper-line" />}

        <dl className="grid grid-cols-[5.5rem_1fr] gap-x-3 gap-y-1.5 text-sm">
          {r.kind === 'ayah' ? (
            <>
              <dt className="text-xs font-medium uppercase tracking-wide text-ink-mute">Passage</dt><dd>Surah {r.surah} · {r.ref}</dd>
              <dt className="text-xs font-medium uppercase tracking-wide text-ink-mute">Reciter</dt><dd>{r.reciter}</dd>
            </>
          ) : (
            <><dt className="text-xs font-medium uppercase tracking-wide text-ink-mute">Dhikr</dt><dd>{r.title}</dd></>
          )}
          <dt className="text-xs font-medium uppercase tracking-wide text-ink-mute">Length</dt><dd className="num">{r.duration}s · {r.size_mb ?? '–'} MB</dd>
          <dt className="text-xs font-medium uppercase tracking-wide text-ink-mute">Loudness</dt><dd className="num">{r.mean_volume_db ?? '–'} dB</dd>
        </dl>

        <div>
          <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-ink-mute">Automatic checks</p>
          <ul className="grid gap-1 sm:grid-cols-2">
            {Object.entries(r.checks ?? {}).map(([k, v]) => (
              <li key={k} className={cn('flex items-center gap-1.5 text-sm', v ? 'text-ink-soft' : 'font-medium text-danger')}>
                {v ? <Check className="h-4 w-4 text-ok" aria-hidden="true" /> : <X className="h-4 w-4" aria-hidden="true" />} {CHECK_LABEL[k] ?? k}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-ink-mute">Caption</p>
          <p className="whitespace-pre-wrap rounded-lg border border-paper-line bg-paper-alt p-3 text-sm">{r.caption}</p>
        </div>

        {r.review && (
          <div className="rounded-lg border border-paper-line p-3 text-sm">
            <p className="text-xs font-semibold text-ink-mute">Review note{r.reviewed ? ` · ${ago(r.reviewed)}` : ''}</p>
            <p className="mt-1 whitespace-pre-wrap">{r.review}</p>
          </div>
        )}

        {r.status === 'pending' && (
          <form onSubmit={(e) => { e.preventDefault(); act.mutate({ type: 'approve', id: r.id, note: note.trim() || undefined }); }} className="flex flex-col gap-2">
            <label className="text-xs font-semibold uppercase tracking-wide text-ink-mute" htmlFor="note">Note</label>
            <textarea id="note" value={note} onChange={(e) => setNote(e.target.value)} rows={2} maxLength={500}
              placeholder="Optional for approve, required to reject (e.g. “text too small on 2nd ayah”)"
              className="w-full rounded-lg border border-paper-line bg-paper p-3 text-sm text-ink placeholder:text-ink-mute focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30" />
            {!ok && <p className="text-xs text-danger">This reel failed an automatic check. Approve only if you're sure it's fine.</p>}
            <div className="flex justify-end gap-2">
              <button type="button" disabled={act.isPending || !note.trim()} onClick={() => act.mutate({ type: 'reject', id: r.id, note: note.trim() })}
                title={note.trim() ? undefined : 'Write why in the note first'}
                className="h-9 cursor-pointer rounded-lg border border-danger/50 px-3 text-sm font-medium text-danger hover:bg-danger-light disabled:cursor-default disabled:opacity-50">Reject</button>
              <button type="submit" disabled={act.isPending}
                className="flex h-9 cursor-pointer items-center gap-2 rounded-lg bg-accent px-3 text-sm font-semibold text-white hover:bg-accent-dark disabled:cursor-default disabled:opacity-50">
                <Check className="h-4 w-4" aria-hidden="true" /> Approve
              </button>
            </div>
          </form>
        )}

        {decided && (
          <div className="flex items-center justify-between gap-2">
            {r.status === 'approved' ? <Badge tone="green">In the posting schedule</Badge> : <span />}
            <button type="button" disabled={act.isPending} onClick={() => act.mutate({ type: 'requeue', id: r.id })}
              className="flex h-9 cursor-pointer items-center gap-2 rounded-lg border border-paper-line px-3 text-sm font-medium text-ink-soft hover:bg-paper-alt disabled:opacity-50">
              <RotateCcw className="h-4 w-4" aria-hidden="true" /> Back to review
            </button>
          </div>
        )}
        </div>
      </div>
    </section>
  );
}
