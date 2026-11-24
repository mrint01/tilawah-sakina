import { useNavigate } from 'react-router-dom';
import { CalendarClock, Hand, CheckCircle2, Clock3, Inbox, Instagram, Play, Power, RefreshCw, Send, Users } from 'lucide-react';
import { cn } from '../admin/cn';
import { nextSlots, postingOrder, slot } from '../admin/api';
import { MakeProgressCard, MakeReelsButton } from '../admin/MakeReels';
import { KindBadge, makingRun, Thumb, useAct, useAppState, useInstagram } from '../admin/hooks';
import { ago, Badge, dateTime, Empty, int, KpiCard, PageHeader, Panel, Skeleton } from '../admin/ui';
import { RunRow } from './RunsPage';
import { TotalsRow } from '../admin/IgStats';

export default function OverviewPage() {
  const navigate = useNavigate();
  const state = useAppState();
  const s = state.data;
  const ig = useInstagram(Boolean(s?.instagram));
  const act = useAct((a) => (a.type === 'toggle' ? `Automation ${a.enabled ? 'ON' : 'OFF'}` : a.type === 'post_now' ? 'Posting started, watch Workflow runs' : 'Generating started, new reels land in Review in ~5 min'));

  const header = (
    <PageHeader
      title="Overview"
      text="Your Quran and tasbih reels: what is waiting, what is scheduled, what went out."
      actions={
        <button type="button" onClick={() => void state.refetch()} className="flex h-9 cursor-pointer items-center gap-2 rounded-lg border border-paper-line bg-paper px-3 text-sm font-medium hover:bg-paper-alt">
          <RefreshCw className={cn('h-4 w-4', state.isFetching && 'animate-spin')} aria-hidden="true" /> Refresh
        </button>
      }
    />
  );

  if (state.error) return <div className="flex flex-col gap-6">{header}<Panel><p className="text-danger">{(state.error as Error).message}</p></Panel></div>;
  if (!s)
    return (
      <div className="flex flex-col gap-6">
        {header}
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-36" />)}</div>
        <Skeleton className="h-56" />
      </div>
    );

  const count = (st: string) => s.items.filter((i) => i.status === st).length;
  const approved = count('approved');
  const pending = count('pending');
  const posted = s.items.filter((i) => i.status === 'posted');
  const upcoming = postingOrder(s.items, s.config.alternate).slice(0, 4);
  const slots = nextSlots(4);
  const followers = ig.data?.profile?.followers_count;

  return (
    <div className="flex flex-col gap-6">
      {header}
      <MakeProgressCard s={s} />

      {pending > 0 && (
        <button type="button" onClick={() => navigate('/review')} className="flex cursor-pointer items-center gap-2 rounded-2xl bg-accent-light p-4 text-start font-semibold text-accent hover:underline">
          <Inbox className="h-5 w-5 shrink-0" aria-hidden="true" />
          {pending === 1 ? '1 reel is waiting for your review' : `${pending} reels are waiting for your review`}
        </button>
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard icon={Users} label="Followers" value={followers ?? 0} tone="violet" delay={0}
          footer={s.instagram ? (ig.data?.profile ? `@${ig.data.profile.username}` : ig.data?.error ?? 'Loading…') : 'Connect Instagram in Settings'} />
        <KpiCard icon={Send} label="Posted" value={posted.length} tone="blue" delay={0.05}
          footer={posted.at(-1)?.posted ? <>Last {ago(posted.at(-1)!.posted!)}</> : 'Nothing posted yet'} onClick={() => navigate('/posted')} />
        <KpiCard icon={CheckCircle2} label="Ready to post" value={approved} tone="green" delay={0.05}
          footer={<>≈ {Math.floor(approved / 2)} {Math.floor(approved / 2) === 1 ? 'day' : 'days'} at 2 a day</>} onClick={() => navigate('/queue')} />
        <KpiCard icon={Inbox} label="Waiting for review" value={pending} tone="orange" delay={0.1}
          footer="Approve or reject in Review" onClick={() => navigate('/review')} />
      </div>

      {s.instagram && <TotalsRow ig={ig.data} />}

      <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <Panel title="Automation" delay={0.1}>
          <div className="flex flex-wrap items-center gap-4">
            <button type="button" role="switch" aria-checked={s.config.enabled} disabled={act.isPending}
              onClick={() => act.mutate({ type: 'toggle', enabled: !s.config.enabled })}
              className={cn('relative h-8 w-14 shrink-0 cursor-pointer rounded-full transition-colors', s.config.enabled ? 'bg-accent' : 'bg-paper-line')}>
              <span className={cn('absolute top-1 h-6 w-6 rounded-full bg-white shadow transition-[left]', s.config.enabled ? 'left-7' : 'left-1')} />
              <span className="sr-only">Automation</span>
            </button>
            <div className="min-w-0 flex-1">
              <p className="flex items-center gap-2 font-semibold">
                <Power className={cn('h-4 w-4', s.config.enabled ? 'text-ok' : 'text-ink-mute')} aria-hidden="true" />
                {s.config.enabled ? 'ON: posting every day' : 'OFF: nothing is made or posted'}
              </p>
              <p className="text-xs text-ink-mute">Posts at 09:00 and 19:00 (Tunisia), alternating {s.config.alternate.join(' → ')}. New reels are made daily at 06:00 until {s.config.buffer} are waiting.</p>
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <button type="button" disabled={act.isPending || approved === 0 || !s.instagram} title={s.instagram ? undefined : 'Connect Instagram first; until then use “Post next by hand”'} onClick={() => act.mutate({ type: 'post_now' })}
              className="flex h-9 cursor-pointer items-center gap-2 rounded-lg bg-accent px-3 text-sm font-semibold text-white hover:bg-accent-dark disabled:cursor-default disabled:opacity-50">
              <Play className="h-4 w-4" aria-hidden="true" /> Post next now
            </button>
            <MakeReelsButton busy={Boolean(makingRun(s))} reciters={Object.keys(s.config.reciters)} />
            {!s.instagram && upcoming[0] && (
              <button type="button" onClick={() => navigate(`/review?reel=${upcoming[0].id}`)}
                className="flex h-9 cursor-pointer items-center gap-2 rounded-lg border border-accent px-3 text-sm font-semibold text-accent hover:bg-accent/10">
                <Hand className="h-4 w-4" aria-hidden="true" /> Post next by hand
              </button>
            )}
            {!s.instagram && (
              <button type="button" onClick={() => navigate('/settings')} className="flex h-9 cursor-pointer items-center gap-2 rounded-lg border border-paper-line px-3 text-sm font-medium text-ink-soft hover:bg-paper-alt">
                <Instagram className="h-4 w-4" aria-hidden="true" /> Connect Instagram
              </button>
            )}
          </div>
        </Panel>

        <Panel title="Up next" delay={0.15} action={<button type="button" onClick={() => navigate('/queue')} className="cursor-pointer text-xs font-medium text-accent hover:underline">All {approved}</button>}>
          {upcoming.length === 0 ? <Empty icon={CalendarClock} text="Nothing approved yet. Review new reels to fill the schedule." /> : (
            <ul className="divide-y divide-paper-line">
              {upcoming.map((r, i) => (
                <li key={r.id} className="flex items-center gap-3 py-2.5">
                  <Thumb state={s} reel={r} className="h-12 w-[27px]" />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium">{r.title}</span>
                    <span className="flex items-center gap-1.5 text-xs text-ink-mute"><KindBadge kind={r.kind} /> {r.duration}s</span>
                  </span>
                  <span className="flex shrink-0 items-center gap-1 text-xs text-ink-mute"><Clock3 className="h-3.5 w-3.5" aria-hidden="true" /> {s.config.enabled ? slot(slots[i]) : 'paused'}</span>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title="Latest posts" delay={0.2} action={<button type="button" onClick={() => navigate('/posted')} className="cursor-pointer text-xs font-medium text-accent hover:underline">All posts</button>}>
          {posted.length === 0 ? <Empty icon={Send} text="No posts yet. The first one goes out at the next slot once Instagram is connected." /> : (
            <ul className="divide-y divide-paper-line">
              {posted.slice(-4).reverse().map((r) => {
                const m = ig.data?.media?.[r.id];
                return (
                  <li key={r.id} className="flex items-center gap-3 py-2.5">
                    <Thumb state={s} reel={r} className="h-12 w-[27px]" />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-medium">{r.title}</span>
                      <span className="text-xs text-ink-mute" title={dateTime(r.posted ?? null)}>{ago(r.posted ?? null)}</span>
                    </span>
                    {m?.views != null && <Badge tone="blue">{int.format(m.views)} views</Badge>}
                  </li>
                );
              })}
            </ul>
          )}
        </Panel>

        <Panel title="Recent workflow runs" delay={0.25} action={<button type="button" onClick={() => navigate('/runs')} className="cursor-pointer text-xs font-medium text-accent hover:underline">All runs</button>}>
          <ul className="divide-y divide-paper-line">{s.runs.slice(0, 5).map((r) => <RunRow key={r.id} run={r} />)}</ul>
        </Panel>
      </div>
    </div>
  );
}
