import { motion } from 'framer-motion';
import { CheckCircle2, ExternalLink, Instagram, Loader2, PartyPopper, TriangleAlert, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { cn } from './cn';
import type { PanelState, PostingProgress } from './api';
import { postingRun } from './hooks';

const STEPS: { key: PostingProgress['stage']; label: string }[] = [
  { key: 'preparing', label: 'Getting the reel ready' },
  { key: 'video', label: 'Preparing the video for Instagram' },
  { key: 'hosting', label: 'Putting it online for Instagram' },
  { key: 'uploading', label: 'Sending it to Instagram' },
  { key: 'processing', label: 'Instagram is processing it' },
  { key: 'publishing', label: 'Publishing' },
  { key: 'live', label: 'Live on @tilawah.sakina' },
];
const ORDER = STEPS.map((s) => s.key);

/** A burst of gold and green dots, once, when the reel goes live. */
function Burst() {
  const dots = Array.from({ length: 26 }, (_, i) => {
    const a = (i / 26) * Math.PI * 2;
    const r = 70 + (i % 3) * 28;
    return { x: Math.cos(a) * r, y: Math.sin(a) * r, c: ['#e8c680', '#3fb37f', '#f5d896', '#9ad8b8'][i % 4], d: (i % 5) * 0.03 };
  });
  return (
    <span className="pointer-events-none absolute inset-0 flex items-center justify-center" aria-hidden="true">
      {dots.map((p, i) => (
        <motion.span key={i} className="absolute h-2 w-2 rounded-full" style={{ background: p.c }}
          initial={{ x: 0, y: 0, opacity: 1, scale: 1 }} animate={{ x: p.x, y: p.y, opacity: 0, scale: 0.4 }}
          transition={{ duration: 1.3, delay: p.d, ease: 'easeOut' }} />
      ))}
    </span>
  );
}

/**
 * Live card while a post runs ("Publish now" or a scheduled slot): the steps with a progress bar, then a short
 * celebration and the link when it is live. Stays a few minutes after it finished, until closed.
 */
export function PublishProgress({ s }: { s: PanelState }) {
  const run = postingRun(s);
  const p = s.posting;
  const recent = p?.updated ? Date.now() - new Date(p.updated).getTime() < 5 * 60_000 : false;
  const mine = p && (run ? p.run_id === String(run.id) : recent);
  const [closed, setClosed] = useState<string | null>(null);
  const key = `${p?.run_id}:${p?.stage}`;
  useEffect(() => { if (p?.stage === 'live' || p?.stage === 'failed') setClosed((c) => (c === key ? c : null)); }, [key]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!run && !(mine && p?.finished)) return null;
  if (closed === key) return null;

  const live = mine && p?.stage === 'live';
  const failed = mine && p?.stage === 'failed';
  const stage = mine ? p!.stage : null;
  const pct = mine ? p!.pct : run?.status === 'in_progress' ? 4 : 0;
  const at = stage ? ORDER.indexOf(stage) : -1;

  return (
    <motion.section initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} aria-live="polite"
      className={cn('relative overflow-hidden rounded-xl border bg-paper p-4 shadow-sm', live ? 'border-ok/60' : failed ? 'border-danger/60' : 'border-paper-line')}>
      {live && <Burst />}
      <div className="flex items-start gap-3">
        <span className={cn('relative flex h-10 w-10 shrink-0 items-center justify-center rounded-xl',
          live ? 'bg-ok-light text-ok' : failed ? 'bg-danger-light text-danger' : 'bg-accent/10 text-accent')}>
          {live ? <PartyPopper className="h-5 w-5" aria-hidden="true" /> : failed ? <TriangleAlert className="h-5 w-5" aria-hidden="true" />
            : <Instagram className="h-5 w-5" aria-hidden="true" />}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline justify-between gap-3">
            <h2 className="text-sm font-semibold">
              {live ? 'It is live on Instagram!' : failed ? 'Publishing failed' : run?.status === 'queued' && !mine ? 'Waiting for GitHub to start…' : 'Publishing to Instagram…'}
            </h2>
            <span className="num text-sm font-semibold text-accent">{pct}%</span>
          </div>
          <p className="truncate text-xs text-ink-mute">{(mine && p?.title) || 'The next reel'}{failed && p?.error ? ` · ${p.error}` : ''}</p>
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-paper-alt" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct}>
            <motion.div className={cn('h-full rounded-full', live ? 'bg-ok' : failed ? 'bg-danger' : 'bg-accent')}
              animate={{ width: `${Math.max(3, pct)}%` }} transition={{ duration: 0.8, ease: 'easeOut' }} />
          </div>
          <ol className="mt-3 grid gap-1 sm:grid-cols-2">
            {STEPS.map((st, i) => {
              const done = live || (at > i);
              const now = !live && !failed && at === i;
              return (
                <li key={st.key} className={cn('flex items-center gap-1.5 text-xs', done ? 'text-ink-soft' : now ? 'font-semibold text-accent' : 'text-ink-mute')}>
                  {done ? <CheckCircle2 className="h-3.5 w-3.5 text-ok" aria-hidden="true" />
                    : now ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                      : <span className="mx-[3px] h-2 w-2 rounded-full border border-ink-mute/50" aria-hidden="true" />}
                  {st.label}
                </li>
              );
            })}
          </ol>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            {live && p?.permalink && (
              <a href={p.permalink} target="_blank" rel="noreferrer"
                className="flex h-9 items-center gap-2 rounded-lg bg-ok px-3 text-sm font-semibold text-white hover:opacity-90">
                <ExternalLink className="h-4 w-4" aria-hidden="true" /> Open the post
              </a>
            )}
            {run && <a href={run.url} target="_blank" rel="noreferrer" className="text-xs text-ink-mute underline hover:text-accent">The run on GitHub</a>}
          </div>
        </div>
        {(live || failed) && (
          <button type="button" aria-label="Close" onClick={() => setClosed(key)}
            className="flex h-8 w-8 shrink-0 cursor-pointer items-center justify-center rounded-md text-ink-mute hover:bg-paper-alt hover:text-ink">
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        )}
      </div>
    </motion.section>
  );
}
