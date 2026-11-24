import { Bookmark, Eye, Heart, MessageCircle, Radar, Share2, Timer, TriangleAlert } from 'lucide-react';
import type { InstagramStats, MediaStats } from './api';
import { int, KpiCard } from './ui';

const METRICS = [
  { key: 'views', label: 'Views', icon: Eye, tone: 'blue' },
  { key: 'likes', label: 'Likes', icon: Heart, tone: 'red' },
  { key: 'comments', label: 'Comments', icon: MessageCircle, tone: 'violet' },
  { key: 'shares', label: 'Shares', icon: Share2, tone: 'green' },
  { key: 'saves', label: 'Saves', icon: Bookmark, tone: 'orange' },
] as const;

/** "Views / Likes / Comments / Shares / Saves" across every post on the account. */
export function TotalsRow({ ig }: { ig?: InstagramStats }) {
  const t = ig?.totals;
  const posts = t?.posts ?? 0;
  return (
    <div className="flex flex-col gap-2">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5">
        {METRICS.map((m, i) => {
          const v = t?.[m.key] ?? null;
          return (
            <KpiCard key={m.key} icon={m.icon} label={`Total ${m.label.toLowerCase()}`} value={v ?? 0} tone={m.tone} delay={0.04 * i}
              footer={!t ? 'Loading…' : v == null ? 'Needs insights permission' : posts ? `≈ ${int.format(Math.round(v / posts))} per post` : '–'} />
          );
        })}
      </div>
      {ig?.insights_error && <InsightsNote text={ig.insights_error} />}
    </div>
  );
}

export function InsightsNote({ text }: { text: string }) {
  return (
    <p className="flex items-start gap-2 rounded-xl bg-accent-light p-3 text-xs font-medium text-accent">
      <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" /> {text} Likes and comments are real already.
    </p>
  );
}

/** The numbers of one post, as a small grid (used on the reel page). */
export function ReelStats({ m }: { m?: MediaStats }) {
  const cells = [...METRICS, { key: 'reach', label: 'Reach', icon: Radar, tone: 'slate' } as const,
    { key: 'watch', label: 'Avg watch', icon: Timer, tone: 'slate' } as const];
  return (
    <dl className="grid grid-cols-3 gap-2 sm:grid-cols-4 2xl:grid-cols-7">
      {cells.map((c) => {
        const v = m ? (m as unknown as Record<string, number | null>)[c.key] : undefined;
        return (
          <div key={c.key} className="rounded-lg border border-paper-line bg-paper-alt px-2 py-2.5 text-center">
            <dt className="flex items-center justify-center gap-1 text-xs text-ink-mute"><c.icon className="h-3.5 w-3.5" aria-hidden="true" /> {c.label}</dt>
            <dd className="num mt-0.5 text-lg font-bold">{v == null ? '–' : c.key === 'watch' ? `${v}s` : int.format(v)}</dd>
          </div>
        );
      })}
    </dl>
  );
}
