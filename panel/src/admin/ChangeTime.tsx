import { useState } from 'react';
import { createPortal } from 'react-dom';
import { CalendarClock, Undo2 } from 'lucide-react';
import { cn } from './cn';
import { slot, type Reel } from './api';
import { useAct } from './hooks';
import { INPUT, Modal, SELECT } from './ui';

// Tunisia is UTC+1 all year (no daylight saving)
const tunisParts = (d: Date) => {
  const t = new Date(d.getTime() + 3600_000);
  return { day: t.toISOString().slice(0, 10), hour: t.getUTCHours() };
};
const fromTunis = (day: string, hour: number) => {
  const [y, m, d] = day.split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, d, hour - 1));
};

/**
 * "Change time" for one approved reel: post it at a chosen day and hour (Tunisia time) instead of at its type's slot,
 * or put it back on the normal schedule. `slot`: from the Not posted page, the missed slot it makes up for.
 */
export function ChangeTime({ r, slot: missed, next, small = false }: { r: Reel; slot?: string; next?: Date; small?: boolean }) {
  const act = useAct((a) => (a.type === 'schedule' && a.at ? 'New time saved' : 'Back to the normal schedule'));
  const [open, setOpen] = useState(false);
  const start = r.post_at ? new Date(r.post_at) : next && next > new Date() ? next : new Date(Date.now() + 3600_000);
  const [day, setDay] = useState(tunisParts(start).day);
  const [hour, setHour] = useState(tunisParts(start).hour);
  const at = fromTunis(day, hour);
  const past = at.getTime() < Date.now() - 5 * 60_000;
  const today = tunisParts(new Date()).day;

  // inside clickable rows: keep clicks in the button and popup from opening the reel
  return (
    <span className="contents" onClick={(e) => e.stopPropagation()}>
      <button type="button" disabled={act.isPending} title={r.post_at ? `Chosen time: ${slot(new Date(r.post_at))}` : 'Post it at another day and hour'}
        onClick={(e) => { e.stopPropagation(); setOpen(true); }}
        className={cn('inline-flex cursor-pointer items-center justify-center gap-1.5 rounded-md border border-paper-line font-medium text-ink-soft hover:border-accent hover:text-accent disabled:opacity-50',
          small ? 'h-8 w-8' : 'h-9 px-3 text-sm')}
        aria-label="Change time">
        <CalendarClock className="h-4 w-4" aria-hidden="true" />{!small && ' Change time'}
      </button>
      {createPortal(<Modal open={open} onClose={() => setOpen(false)} title="When should it be posted?" icon={CalendarClock}
        text="Tunisia time. It goes out a few minutes after the hour you pick, instead of at its type's usual slot.">
        <div onClick={(e) => e.stopPropagation()} className="flex flex-col gap-3 whitespace-normal text-start">
          <p className="text-sm font-semibold">{r.title}</p>
          <div className="grid grid-cols-[1fr_8rem] gap-2">
            <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-wide text-ink-mute">Day
              <input type="date" className={INPUT} value={day} min={today} onChange={(e) => setDay(e.target.value)} />
            </label>
            <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-wide text-ink-mute">Hour
              <select className={SELECT} value={hour} onChange={(e) => setHour(Number(e.target.value))}>
                {Array.from({ length: 24 }, (_, h) => <option key={h} value={h}>{String(h).padStart(2, '0')}:00</option>)}
              </select>
            </label>
          </div>
          {past && <p role="alert" className="text-xs font-medium text-danger">That time has passed: pick a later one.</p>}
          <div className="flex flex-wrap justify-end gap-2 pt-1">
            {r.post_at && (
              <button type="button" disabled={act.isPending}
                onClick={() => act.mutate({ type: 'schedule', id: r.id, at: null }, { onSuccess: () => setOpen(false) })}
                className="me-auto flex h-10 cursor-pointer items-center gap-2 rounded-lg border border-paper-line px-3 text-sm font-medium text-ink-soft hover:bg-paper-alt">
                <Undo2 className="h-4 w-4" aria-hidden="true" /> Normal schedule
              </button>
            )}
            <button type="button" onClick={() => setOpen(false)}
              className="h-10 cursor-pointer rounded-lg border border-paper-line px-4 text-sm font-medium text-ink-soft hover:bg-paper-alt">Cancel</button>
            <button type="button" disabled={act.isPending || past || !day}
              onClick={() => act.mutate({ type: 'schedule', id: r.id, at: at.toISOString(), slot: missed }, { onSuccess: () => setOpen(false) })}
              className="flex h-10 cursor-pointer items-center gap-2 rounded-lg bg-accent px-4 text-sm font-semibold text-white hover:bg-accent-dark disabled:opacity-50">
              <CalendarClock className="h-4 w-4" aria-hidden="true" /> Save time
            </button>
          </div>
        </div>
      </Modal>, document.body)}
    </span>
  );
}
