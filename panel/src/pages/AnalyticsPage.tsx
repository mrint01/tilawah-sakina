import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowDownRight, ArrowUpRight, Bookmark, Eye, Heart, MessageCircle, Radar, RefreshCw, Share2, Trophy, Users } from 'lucide-react';
import { cn } from '../admin/cn';
import { api, type DayStats, type Kind, type MediaStats, type Reel } from '../admin/api';
import { AreaChart } from '../admin/charts';
import { KIND, KindBadge, Thumb, useAppState, useInstagram } from '../admin/hooks';
import { Empty, INPUT, int, PageHeader, Panel, SELECT, Skeleton } from '../admin/ui';

type Metric = 'followers' | 'views' | 'reach' | 'likes' | 'shares' | 'saves' | 'comments';
const METRICS: { key: Metric; label: string; icon: typeof Eye; hint: string }[] = [
  { key: 'followers', label: 'Followers', icon: Users, hint: 'People following @tilawah.sakina, at the end of each day' },
  { key: 'views', label: 'Views', icon: Eye, hint: 'Times your reels and posts were played or shown' },
  { key: 'reach', label: 'Reach', icon: Radar, hint: 'Different accounts that saw something of yours that day' },
  { key: 'likes', label: 'Likes', icon: Heart, hint: 'Likes on all your posts that day' },
  { key: 'shares', label: 'Shares', icon: Share2, hint: 'Times your posts were sent to someone' },
  { key: 'saves', label: 'Saves', icon: Bookmark, hint: 'Times your posts were saved' },
  { key: 'comments', label: 'Comments', icon: MessageCircle, hint: 'Comments on your posts that day' },
];
type Period = '7' | '30' | '90' | 'custom';
type Top = 'views' | 'likes' | 'shares' | 'saves' | 'comments' | 'watch';
const TOP: { key: Top; label: string }[] = [
  { key: 'views', label: 'Views' }, { key: 'likes', label: 'Likes' }, { key: 'shares', label: 'Shares' },
  { key: 'saves', label: 'Saves' }, { key: 'comments', label: 'Comments' }, { key: 'watch', label: 'Watch time' },
];

// Tunisia days (UTC+1, no daylight saving)
const tunisDay = (d: Date) => new Date(d.getTime() + 3600_000).toISOString().slice(0, 10);
const addDays = (day: string, n: number) => new Date(Date.parse(`${day}T12:00:00Z`) + n * 86400_000).toISOString().slice(0, 10);
const span = (from: string, to: string) => {
  const out: string[] = [];
  for (let d = from; d <= to && out.length < 400; d = addDays(d, 1)) out.push(d);
  return out;
};
const short = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' });
const long = new Intl.DateTimeFormat('en-GB', { weekday: 'short', day: 'numeric', month: 'short', timeZone: 'UTC' });
const dayLabel = (d: string, f = short) => f.format(new Date(`${d}T12:00:00Z`));
const compact = new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 });
const pct = (v: number) => `${v >= 0 ? '+' : ''}${Math.round(v)}%`;

export default function AnalyticsPage() {
  const navigate = useNavigate();
  const state = useAppState();
  const s = state.data;
  const ig = useInstagram(Boolean(s?.instagram));
  const an = useQuery({ queryKey: ['analytics'], queryFn: api.analytics, staleTime: 5 * 60_000 });
  const [metric, setMetric] = useState<Metric>('followers');
  const [period, setPeriod] = useState<Period>('30');
  const today = tunisDay(new Date());
  const [custom, setCustom] = useState({ from: addDays(today, -13), to: today });
  const [top, setTop] = useState<Top>('views');

  const days = an.data?.days ?? {};
  const range = period === 'custom' ? { from: custom.from <= custom.to ? custom.from : custom.to, to: custom.to >= custom.from ? custom.to : custom.from } : { from: addDays(today, -(Number(period) - 1)), to: today };
  const list = span(range.from, range.to);
  const len = list.length;
  const prevList = span(addDays(range.from, -len), addDays(range.from, -1));
  const firstDay = Object.keys(days).sort()[0];

  const value = (d: string, m: Metric): number | null => {
    const row: DayStats | undefined = days[d];
    const v = row?.[m];
    if (v != null) return v;
    if (m === 'followers') return null;
    return firstDay && d >= firstDay && d <= today ? (row ? 0 : null) : null;
  };
  const sum = (ds: string[], m: Metric) => ds.reduce((a, d) => a + (value(d, m) ?? 0), 0);
  const followerPoints = list.map((d) => value(d, 'followers')).filter((v): v is number => v != null);
  const followersNow = ig.data?.profile?.followers_count ?? followerPoints.at(-1) ?? null;
  const tile = (m: Metric) => {
    if (m === 'followers') {
      const first = followerPoints[0];
      return { value: followersNow, change: followersNow != null && first != null && followerPoints.length > 1 ? followersNow - first : null, kind: 'count' as const };
    }
    const now = sum(list, m);
    const before = sum(prevList, m);
    const hasPrev = prevList.some((d) => days[d]?.[m] != null);
    return { value: now, change: hasPrev && before > 0 ? ((now - before) / before) * 100 : null, kind: 'pct' as const };
  };
  const chart = list.map((d) => ({ label: dayLabel(d, len > 14 ? short : long), value: value(d, metric) }));
  const recorded = Object.entries(days).filter(([, r]) => r.followers != null).map(([d]) => d).sort();

  // posts in the period, with their reel from the queue
  const byId = useMemo(() => new Map((s?.items ?? []).map((r) => [r.id, r])), [s]);
  const posts = (ig.data?.posts ?? []).filter((p) => p.timestamp && tunisDay(new Date(p.timestamp)) >= range.from && tunisDay(new Date(p.timestamp)) <= range.to);
  const topVal = (p: MediaStats) => (top === 'watch' ? p.watch ?? -1 : (p[top] as number | null) ?? -1);
  const best = [...posts].sort((a, b) => topVal(b) - topVal(a)).slice(0, 5);
  const bestMax = Math.max(1, ...best.map(topVal));

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="Analytics" text="How @tilawah.sakina grows: the account day by day, the best reels and what works."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex rounded-lg border border-paper-line bg-paper p-0.5" role="tablist" aria-label="Period">
              {(['7', '30', '90', 'custom'] as Period[]).map((p) => (
                <button key={p} type="button" role="tab" aria-selected={period === p} onClick={() => setPeriod(p)}
                  className={cn('h-8 cursor-pointer rounded-md px-3 text-xs font-semibold', period === p ? 'bg-accent text-white' : 'text-ink-soft hover:text-ink')}>
                  {p === 'custom' ? 'Custom' : `${p}d`}
                </button>
              ))}
            </div>
            <button type="button" onClick={() => { void an.refetch(); void ig.refetch(); }}
              className="flex h-9 cursor-pointer items-center gap-2 rounded-lg border border-paper-line bg-paper px-3 text-sm font-medium hover:bg-paper-alt">
              <RefreshCw className={cn('h-4 w-4', (an.isFetching || ig.isFetching) && 'animate-spin')} aria-hidden="true" /> Refresh
            </button>
          </div>
        } />
      {period === 'custom' && (
        <div className="flex flex-wrap items-end gap-2">
          <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-wide text-ink-mute">From
            <input type="date" className={cn(INPUT, 'w-44')} value={custom.from} max={today} onChange={(e) => setCustom((c) => ({ ...c, from: e.target.value }))} />
          </label>
          <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-wide text-ink-mute">To
            <input type="date" className={cn(INPUT, 'w-44')} value={custom.to} max={today} onChange={(e) => setCustom((c) => ({ ...c, to: e.target.value }))} />
          </label>
          <p className="pb-2.5 text-xs text-ink-mute">{len} days</p>
        </div>
      )}

      {/* the chart first: pick the number with the tiles above it */}
      <section className="rounded-xl border border-paper-line bg-paper shadow-sm">
        <div className="grid grid-cols-2 gap-px overflow-hidden rounded-t-xl border-b border-paper-line bg-paper-line sm:grid-cols-4 xl:grid-cols-7">
          {METRICS.map((m) => {
            const t = tile(m.key);
            const on = metric === m.key;
            return (
              <button key={m.key} type="button" onClick={() => setMetric(m.key)} aria-pressed={on} title={m.hint}
                className={cn('relative cursor-pointer bg-paper px-4 py-3 text-start transition-colors hover:bg-paper-alt', on && 'bg-accent/5', m.key === 'comments' && 'col-span-2 xl:col-span-1')}>
                {on && <span className="absolute inset-x-0 top-0 h-[3px] bg-accent" aria-hidden="true" />}
                <span className={cn('flex items-center gap-1.5 text-xs font-medium', on ? 'text-accent' : 'text-ink-mute')}>
                  <m.icon className="h-3.5 w-3.5" aria-hidden="true" /> {m.label}
                </span>
                <span className="num mt-1 block text-xl font-bold">{an.isLoading ? '…' : t.value == null ? '–' : compact.format(t.value)}</span>
                <span className={cn('flex items-center gap-0.5 text-xs', t.change == null ? 'text-ink-mute' : t.change >= 0 ? 'text-ok' : 'text-danger')}>
                  {t.change == null ? (m.key === 'followers' ? 'now' : `in ${len} days`) : (
                    <>{t.change >= 0 ? <ArrowUpRight className="h-3 w-3" aria-hidden="true" /> : <ArrowDownRight className="h-3 w-3" aria-hidden="true" />}
                      {t.kind === 'pct' ? `${pct(t.change)} vs the ${len} days before` : `${t.change >= 0 ? '+' : ''}${t.change} in ${len} days`}</>
                  )}
                </span>
              </button>
            );
          })}
        </div>
        <div className="p-4">
          <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-sm font-semibold">{METRICS.find((m) => m.key === metric)!.label}{metric === 'followers' ? '' : ' per day'}</h2>
            <p className="text-xs text-ink-mute">{dayLabel(range.from, long)} – {dayLabel(range.to, long)} · Tunisia time</p>
          </div>
          {an.isLoading ? <Skeleton className="h-64" /> : (
            <AreaChart data={chart} label={METRICS.find((m) => m.key === metric)!.label} zero={metric !== 'followers'} format={(v) => compact.format(v)} />
          )}
          {metric === 'followers' && recorded.length < 7 && (
            <p className="mt-2 rounded-lg bg-paper-alt p-2.5 text-xs text-ink-soft">
              Instagram only gives a day-by-day follower history from 100 followers, so the panel records the count itself every 6 hours
              {recorded[0] ? `, since ${dayLabel(recorded[0], long)}` : ''}. The line grows from here; views, reach, likes, shares and saves go back 90 days.
            </p>
          )}
        </div>
      </section>

      <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-2">
        <Panel title={<span className="flex items-center gap-2"><Trophy className="h-4 w-4 text-accent" aria-hidden="true" /> Best reels</span>}
          action={
            <select className={SELECT} value={top} onChange={(e) => setTop(e.target.value as Top)} aria-label="Rank by">
              {TOP.map((t) => <option key={t.key} value={t.key}>By {t.label.toLowerCase()}</option>)}
            </select>
          }>
          {!s?.instagram ? <Empty icon={Trophy} text="Connect Instagram to see the best reels." /> : ig.isLoading ? <Skeleton className="h-56" /> : best.length === 0 ? (
            <Empty icon={Trophy} text="Nothing posted in this period." />
          ) : (
            <ol className="flex flex-col gap-1">
              {best.map((p, i) => {
                const r = p.reel ? byId.get(p.reel) : undefined;
                const v = topVal(p);
                return (
                  <li key={p.id}>
                    <button type="button" onClick={() => (r ? navigate(`/review?reel=${r.id}`) : p.permalink && window.open(p.permalink, '_blank'))}
                      className="flex w-full cursor-pointer items-center gap-3 rounded-lg p-2 text-start hover:bg-paper-alt">
                      <span className={cn('num flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold', i === 0 ? 'bg-accent text-white' : 'bg-paper-alt text-ink-soft')}>{i + 1}</span>
                      {r && s ? <Thumb state={s} reel={r} className="h-12 w-[27px]" />
                        : p.thumbnail ? <img src={p.thumbnail} alt="" className="h-12 w-[27px] shrink-0 rounded-md object-cover" /> : <span className="h-12 w-[27px] shrink-0 rounded-md bg-paper-alt" />}
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-semibold">{r?.title ?? ((p.caption || '').split('\n')[0] || 'Post')}</span>
                        <span className="mt-1 flex items-center gap-2">
                          {r && <KindBadge kind={r.kind} />}
                          <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-paper-alt">
                            <span className="block h-full rounded-full bg-accent" style={{ width: `${Math.max(3, (Math.max(0, v) / bestMax) * 100)}%` }} />
                          </span>
                        </span>
                      </span>
                      <span className="num w-20 shrink-0 text-right text-sm font-bold">{v < 0 ? '–' : top === 'watch' ? `${v.toFixed(1)}s` : int.format(v)}</span>
                    </button>
                  </li>
                );
              })}
            </ol>
          )}
        </Panel>

        <TypeMix posts={posts} byId={byId} loading={ig.isLoading} connected={Boolean(s?.instagram)} />
      </div>

      <ViewsCalendar days={days} today={today} loading={an.isLoading} />
    </div>
  );
}

/** Which type of reel does best: average views per post and how many viewers like, save, share or comment. */
function TypeMix({ posts, byId, loading, connected }: { posts: MediaStats[]; byId: Map<string, Reel>; loading: boolean; connected: boolean }) {
  const rows = (Object.keys(KIND) as Kind[]).map((k) => {
    const ps = posts.filter((p) => p.reel && byId.get(p.reel)?.kind === k && p.views != null);
    const views = ps.reduce((a, p) => a + (p.views ?? 0), 0);
    const acts = ps.reduce((a, p) => a + p.likes + p.comments + (p.saves ?? 0) + (p.shares ?? 0), 0);
    return { k, n: ps.length, avg: ps.length ? views / ps.length : 0, eng: views ? (acts / views) * 100 : 0 };
  }).filter((r) => r.n > 0).sort((a, b) => b.avg - a.avg);
  const max = Math.max(1, ...rows.map((r) => r.avg));
  return (
    <Panel title="What works best">
      {!connected ? <Empty icon={Eye} text="Connect Instagram to compare the types." /> : loading ? <Skeleton className="h-56" /> : rows.length === 0 ? (
        <Empty icon={Eye} text="No reels from the queue posted in this period." />
      ) : (
        <>
          <p className="mb-3 text-xs text-ink-mute">Average views per reel, and engagement: likes, comments, saves and shares per 100 views.</p>
          <ul className="flex flex-col gap-3">
            {rows.map((r, i) => (
              <li key={r.k} className="grid grid-cols-[7.5rem_1fr_auto] items-center gap-3">
                <span className="flex items-center gap-1.5"><KindBadge kind={r.k} />{i === 0 && rows.length > 1 && <span title="Most views per reel">🏆</span>}</span>
                <span className="h-2.5 overflow-hidden rounded-full bg-paper-alt" title={`${int.format(Math.round(r.avg))} views per reel, ${r.n} reels`}>
                  <span className="block h-full rounded-full bg-accent" style={{ width: `${Math.max(3, (r.avg / max) * 100)}%` }} />
                </span>
                <span className="num w-36 text-right text-xs">
                  <b className="text-sm text-ink">{compact.format(Math.round(r.avg))}</b> <span className="text-ink-mute">views · {r.eng.toFixed(1)}% eng.</span>
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-ink-mute">{rows.reduce((a, r) => a + r.n, 0)} reels in this period.</p>
        </>
      )}
    </Panel>
  );
}

/** The last 13 weeks, one square per day, darker = more views (a year-in-pixels style calendar). */
function ViewsCalendar({ days, today, loading }: { days: Record<string, DayStats>; today: string; loading: boolean }) {
  const [hover, setHover] = useState<string | null>(null);
  // start on a Monday, 13 weeks back
  const dow = (new Date(`${today}T12:00:00Z`).getUTCDay() + 6) % 7;
  const start = addDays(today, -(12 * 7 + dow));
  const cells = span(start, addDays(start, 13 * 7 - 1));
  const vals = cells.map((d) => days[d]?.views ?? 0).filter((v) => v > 0).sort((a, b) => a - b);
  const q = (p: number) => vals[Math.min(vals.length - 1, Math.floor(p * vals.length))] ?? 0;
  const steps = [q(0.25), q(0.5), q(0.75)];
  const level = (v: number) => (v <= 0 ? 0 : v <= steps[0] ? 1 : v <= steps[1] ? 2 : v <= steps[2] ? 3 : 4);
  const OPACITY = [0, 0.25, 0.45, 0.7, 1];
  const total = cells.reduce((a, d) => a + (days[d]?.views ?? 0), 0);
  const bestDay = cells.reduce<string | null>((b, d) => ((days[d]?.views ?? 0) > (b ? days[b]?.views ?? 0 : 0) ? d : b), null);
  const h = hover ? days[hover] : null;
  return (
    <Panel title="Views calendar, last 13 weeks"
      action={<span className="text-xs text-ink-mute">{compact.format(total)} views{bestDay ? ` · best day ${dayLabel(bestDay, long)}` : ''}</span>}>
      {loading ? <Skeleton className="h-32" /> : (
        <div className="flex flex-col gap-3">
          <div className="flex gap-2 overflow-x-auto pb-1">
            <div className="grid shrink-0 grid-rows-7 gap-1 pt-0 text-[12px] leading-[14px] text-ink-mute" aria-hidden="true">
              {['Mon', '', 'Wed', '', 'Fri', '', 'Sun'].map((l, i) => <span key={i} className="h-[14px] sm:h-4">{l}</span>)}
            </div>
            <div className="grid grid-flow-col grid-rows-7 gap-1" role="grid" aria-label="Views per day">
              {cells.map((d) => {
                const v = days[d]?.views ?? 0;
                const future = d > today;
                return (
                  <span key={d} role="gridcell" tabIndex={-1} aria-label={`${dayLabel(d, long)}: ${v} views`}
                    onPointerEnter={() => setHover(d)} onPointerLeave={() => setHover(null)}
                    className={cn('h-[14px] w-[14px] rounded-[3px] sm:h-4 sm:w-4', future ? 'bg-transparent' : 'bg-paper-line', hover === d && 'ring-2 ring-ink/40')}>
                    {!future && v > 0 && <span className="block h-full w-full rounded-[3px] bg-accent" style={{ opacity: OPACITY[level(v)] }} />}
                  </span>
                );
              })}
            </div>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-ink-mute">
            <span className="min-h-[1rem]">
              {hover ? <><b className="text-ink">{dayLabel(hover, long)}</b>: {int.format(h?.views ?? 0)} views · {int.format(h?.likes ?? 0)} likes · {int.format(h?.reach ?? 0)} reached</> : 'Point at a day to see its numbers.'}
            </span>
            <span className="flex items-center gap-1">Less
              {OPACITY.map((o, i) => <span key={i} className="h-3 w-3 rounded-[3px] bg-paper-line">{i > 0 && <span className="block h-full w-full rounded-[3px] bg-accent" style={{ opacity: o }} />}</span>)}
              More</span>
          </div>
        </div>
      )}
    </Panel>
  );
}
