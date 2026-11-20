import { useState } from 'react';
import type { Reel } from './api';
import { SELECT } from './ui';

export interface Filters { kind: 'all' | 'ayah' | 'tasbih'; reciter: string; surah: string }
const NONE: Filters = { kind: 'all', reciter: '', surah: '' };

export const useReelFilters = () => useState<Filters>(NONE);

export const matchFilters = (r: Reel, f: Filters) =>
  (f.kind === 'all' || r.kind === f.kind) && (!f.reciter || r.reciter === f.reciter) && (!f.surah || r.surah === f.surah);

/** Type / reciter / surah filters over a list of reels. Counts are of the whole list. */
export function ReelFilterBar({ items, value, onChange, shown }: { items: Reel[]; value: Filters; onChange: (f: Filters) => void; shown: number }) {
  const uniq = (key: 'reciter' | 'surah') => [...new Set(items.map((r) => r[key]).filter((x): x is string => Boolean(x)))].sort();
  const count = (p: (r: Reel) => boolean) => items.filter(p).length;
  const set = (patch: Partial<Filters>) => {
    const next = { ...value, ...patch };
    if (patch.kind === 'tasbih') { next.reciter = ''; next.surah = ''; }
    if (patch.reciter || patch.surah) next.kind = 'ayah'; // reciters and surahs only exist on ayah reels
    onChange(next);
  };
  const active = value.kind !== 'all' || value.reciter || value.surah;
  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-paper-line px-4 py-3">
      <select aria-label="Type" value={value.kind} onChange={(e) => set({ kind: e.target.value as Filters['kind'] })} className={SELECT}>
        <option value="all">All types ({items.length})</option>
        <option value="ayah">Ayah ({count((r) => r.kind === 'ayah')})</option>
        <option value="tasbih">Tasbih ({count((r) => r.kind === 'tasbih')})</option>
      </select>
      <select aria-label="Surah" value={value.surah} disabled={value.kind === 'tasbih'} onChange={(e) => set({ surah: e.target.value })} className={`${SELECT} max-w-[11rem] disabled:opacity-50`}>
        <option value="">All surahs</option>
        {uniq('surah').map((n) => <option key={n} value={n}>{n} ({count((r) => r.surah === n)})</option>)}
      </select>
      <select aria-label="Reciter" value={value.reciter} disabled={value.kind === 'tasbih'} onChange={(e) => set({ reciter: e.target.value })} className={`${SELECT} max-w-[11rem] disabled:opacity-50`}>
        <option value="">All reciters</option>
        {uniq('reciter').map((n) => <option key={n} value={n}>{n} ({count((r) => r.reciter === n)})</option>)}
      </select>
      {active && (
        <button type="button" onClick={() => onChange(NONE)} className="h-9 cursor-pointer rounded-lg px-2 text-sm text-ink-mute underline hover:text-accent">Clear</button>
      )}
      <span className="ms-auto text-xs text-ink-mute">{shown} shown</span>
    </div>
  );
}
