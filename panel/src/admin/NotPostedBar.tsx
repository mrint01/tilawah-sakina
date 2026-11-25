import { useNavigate } from 'react-router-dom';
import { CalendarX2, ChevronRight } from 'lucide-react';
import { notPosted, slotWhen, type PanelState } from './api';
import { KindBadge } from './hooks';

/** Red bar listing exactly which reels did not go out; gone once every one is published or kept in the schedule. */
export function NotPostedBar({ s }: { s: PanelState }) {
  const navigate = useNavigate();
  const rows = notPosted(s);
  if (!rows.length) return null;
  return (
    <section className="rounded-xl border border-danger/40 bg-danger-light/40 p-3 shadow-sm" aria-label="Not posted">
      <button type="button" onClick={() => navigate('/not-posted')}
        className="flex w-full cursor-pointer items-center gap-2 text-start text-sm font-semibold text-danger hover:underline">
        <CalendarX2 className="h-4 w-4 shrink-0" aria-hidden="true" />
        <span className="flex-1">{rows.length === 1 ? '1 reel was not posted' : `${rows.length} reels were not posted`}: publish it or keep it in the schedule</span>
        <ChevronRight className="h-4 w-4" aria-hidden="true" />
      </button>
      <ul className="mt-2 flex flex-col gap-1.5">
        {rows.map(({ key, entry: e, reel: r }) => (
          <li key={key} className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs">
            <span className="num font-semibold text-ink">{slotWhen(key)}</span>
            <KindBadge kind={e.kind} />
            <span className="min-w-0 flex-1 truncate font-medium text-ink-soft">{r?.title ?? 'No approved reel of this type left'}</span>
            <span className="basis-full text-ink-mute sm:basis-auto">{e.status === 'failed' ? 'Failed, trying again' : e.reason}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
