import { useState } from 'react';
import { CalendarSync, ChevronDown, ExternalLink } from 'lucide-react';
import { cn } from './cn';
import { slot, type PanelState, type WeeklyReel } from './api';
import { ManualPost } from './ManualPost';
import { ago, Badge } from './ui';

/** Next Friday at the reel's time (Tunisia = UTC+1, no daylight saving), as a Date. */
function nextFriday(time: string, now = new Date()) {
  const [h, m] = time.split(':').map(Number);
  const d = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), h - 1, m));
  while (d.getUTCDay() !== 5 || d <= now) d.setUTCDate(d.getUTCDate() + 1);
  return d;
}

/** "Every Friday": the weekly reels (Surah Al-Kahf in 2 parts), with player, caption and download. */
export function WeeklySection({ s }: { s: PanelState }) {
  const [open, setOpen] = useState<string | null>(null);
  if (!s.weekly?.items.length) return null;
  return (
    <section className="overflow-hidden rounded-xl border border-paper-line bg-paper shadow-sm">
      <div className="flex items-center gap-3 border-b border-paper-line px-4 py-3">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent/[.12] text-accent"><CalendarSync className="h-4 w-4" aria-hidden="true" /></span>
        <div className="min-w-0 flex-1">
          <h2 className="text-sm font-semibold">Every Friday</h2>
          <p className="text-xs text-ink-mute">Posted again every week. These videos are kept for good, never deleted.</p>
        </div>
      </div>
      <ul className="divide-y divide-paper-line">
        {s.weekly.items.map((w) => (
          <WeeklyRow key={w.id} s={s} w={w} open={open === w.id} onToggle={() => setOpen(open === w.id ? null : w.id)} />
        ))}
      </ul>
    </section>
  );
}

function WeeklyRow({ s, w, open, onToggle }: { s: PanelState; w: WeeklyReel; open: boolean; onToggle: () => void }) {
  const last = [...s.weekly.posted].reverse().find((p) => p.id === w.id);
  const v = w.made ? `?v=${encodeURIComponent(w.made)}` : ''; // new file after a remake: skip the cached old one
  const mins = `${Math.floor(w.duration / 60)}:${String(Math.round(w.duration % 60)).padStart(2, '0')} min`;
  return (
    <li>
      <button type="button" onClick={onToggle} aria-expanded={open} className="flex w-full cursor-pointer items-start gap-3 px-4 py-3 text-start hover:bg-paper-alt">
        <span className="block h-14 w-8 shrink-0 overflow-hidden rounded-md border border-paper-line bg-paper-alt bg-no-repeat"
          style={{ backgroundImage: `url(${s.weekly.assets}${w.id}${w.cover ? '-cover.jpg' : '.png'}${v})`, backgroundSize: w.cover ? 'cover' : 'auto 100%', backgroundPosition: w.cover ? 'center' : 'left center' }} aria-hidden="true" />
        <span className="min-w-0 flex-1">
          <span className="line-clamp-2 text-sm font-semibold">{w.title}</span>
          <span className="mt-1.5 flex flex-wrap items-center gap-2 text-xs text-ink-soft">
            <Badge tone="violet">Weekly</Badge>
            <span>Every {w.day} {w.time}</span>
            <span>·</span>
            <span className="num">{mins}</span>
            <span>·</span>
            <span>Next: <span className="font-semibold text-ok">{slot(nextFriday(w.time))}</span></span>
          </span>
          <span className="mt-1 block text-xs text-ink-mute">{last ? <>Last posted {ago(last.at)}</> : 'Not posted yet'}</span>
        </span>
        <ChevronDown className={cn('mt-1 h-4 w-4 shrink-0 text-ink-mute transition-transform', open && 'rotate-180')} aria-hidden="true" />
      </button>
      {open && (
        <div className="flex flex-col gap-3 px-4 pb-4">
          <video key={w.id} src={`/api/video?id=${encodeURIComponent(w.id)}${w.made ? `&v=${encodeURIComponent(w.made)}` : ''}#t=0.5`} controls playsInline preload="metadata"
            className="mx-auto aspect-[9/16] max-h-[60vh] w-auto rounded-lg border border-paper-line bg-black" />
          <p className="whitespace-pre-wrap rounded-lg border border-paper-line bg-paper-alt p-3 text-sm">{w.caption}</p>
          <ManualPost reel={w} weekly />
          {last?.permalink && (
            <a href={last.permalink} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-xs text-accent hover:underline">
              <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" /> Last post on Instagram
            </a>
          )}
        </div>
      )}
    </li>
  );
}
