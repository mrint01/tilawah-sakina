import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowDown, ArrowUp, ArrowUpDown, ExternalLink, RefreshCw, Send } from 'lucide-react';
import { cn } from '../admin/cn';
import type { MediaStats, Reel } from '../admin/api';
import { KindBadge, Thumb, useAppState, useInstagram } from '../admin/hooks';
import { matchFilters, ReelFilterBar, useReelFilters } from '../admin/ReelFilters';
import { ago, dateTime, Empty, int, PageHeader, Pager, Skeleton, usePaged } from '../admin/ui';
import { TotalsRow } from '../admin/IgStats';

type Sort = 'posted' | 'views' | 'likes';

export default function PostedPage() {
  const navigate = useNavigate();
  const state = useAppState();
  const s = state.data;
  const ig = useInstagram(Boolean(s?.instagram));
  const [sort, setSort] = useState<{ key: Sort; dir: 1 | -1 }>({ key: 'posted', dir: -1 });
  const stats = (r: Reel): MediaStats | undefined => ig.data?.media?.[r.id];
  const val = (r: Reel) => (sort.key === 'posted' ? +new Date(r.posted ?? 0) : sort.key === 'views' ? stats(r)?.views ?? -1 : stats(r)?.likes ?? -1);
  const allPosted = (s?.items ?? []).filter((i) => i.status === 'posted');
  const [filters, setFilters] = useReelFilters();
  const posted = allPosted.filter((r) => matchFilters(r, filters)).sort((a, b) => (val(a) - val(b)) * sort.dir);
  const paged = usePaged(posted, `${sort.key}${sort.dir}${JSON.stringify(filters)}`, 15);

  const th = (key: Sort, label: string, right = false) => {
    const active = sort.key === key;
    const Icon = !active ? ArrowUpDown : sort.dir === 1 ? ArrowUp : ArrowDown;
    return (
      <th className={cn('px-4 py-2.5 font-semibold', right && 'text-right')}>
        <button type="button" onClick={() => setSort({ key, dir: active ? (sort.dir === 1 ? -1 : 1) : -1 })} className="inline-flex cursor-pointer items-center gap-1 uppercase hover:text-ink">
          {label} <Icon className="h-3 w-3" aria-hidden="true" />
        </button>
      </th>
    );
  };

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Posted"
        text={s ? `${allPosted.length} reels on @tilawah.sakina.` : 'Loading…'}
        actions={
          <button type="button" onClick={() => void ig.refetch()} disabled={!s?.instagram}
            className="flex h-9 cursor-pointer items-center gap-2 rounded-lg border border-paper-line bg-paper px-3 text-sm font-medium hover:bg-paper-alt disabled:opacity-50">
            <RefreshCw className={cn('h-4 w-4', ig.isFetching && 'animate-spin')} aria-hidden="true" /> Refresh stats
          </button>
        }
      />
      {s && !s.instagram && <p className="rounded-xl bg-accent-light p-3 text-sm font-medium text-accent">Views and likes show here once Instagram is connected (Settings → Connections).</p>}
      {ig.data?.error && <p className="rounded-xl bg-danger-light p-3 text-sm text-danger">Instagram: {ig.data.error}</p>}

      {s?.instagram && <TotalsRow ig={ig.data} />}

      <section className="overflow-hidden rounded-xl border border-paper-line bg-paper shadow-sm">
        {s && allPosted.length > 0 && <ReelFilterBar items={allPosted} value={filters} onChange={setFilters} shown={posted.length} />}
        {!s ? <div className="p-4"><Skeleton className="h-40" /></div> : posted.length === 0 ? (
          <Empty icon={Send} text={allPosted.length ? 'No posted reels match these filters.' : 'Nothing posted yet.'} />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-paper-line text-left text-xs uppercase text-ink-mute">
                  <th className="px-4 py-2.5 font-semibold">Reel</th>
                  <th className="px-4 py-2.5 font-semibold">Type</th>
                  {th('posted', 'Posted')}
                  {th('views', 'Views', true)}
                  {th('likes', 'Likes', true)}
                  <th className="px-4 py-2.5 text-right font-semibold">Comments</th>
                  <th className="px-4 py-2.5 text-right font-semibold">Saves</th>
                  <th className="px-4 py-2.5 text-right font-semibold">Shares</th>
                  <th className="px-4 py-2.5" />
                </tr>
              </thead>
              <tbody className="divide-y divide-paper-line">
                {paged.items?.map((r) => {
                  const m = stats(r);
                  const n = (v: number | null | undefined) => (v == null ? '–' : int.format(v));
                  return (
                    <tr key={r.id} onClick={() => navigate(`/review?reel=${r.id}`)} className="cursor-pointer hover:bg-paper-alt">
                      <td className="px-4 py-2.5">
                        <span className="flex items-center gap-3">
                          <Thumb state={s} reel={r} className="h-12 w-[27px]" />
                          <span className="block max-w-[18rem] truncate font-semibold">{r.title}</span>
                        </span>
                      </td>
                      <td className="px-4 py-2.5"><KindBadge kind={r.kind} /></td>
                      <td className="px-4 py-2.5 text-ink-soft" title={dateTime(r.posted ?? null)}>{ago(r.posted ?? null)}</td>
                      <td className="num px-4 py-2.5 text-right font-semibold">{n(m?.views)}</td>
                      <td className="num px-4 py-2.5 text-right">{n(m?.likes)}</td>
                      <td className="num px-4 py-2.5 text-right">{n(m?.comments)}</td>
                      <td className="num px-4 py-2.5 text-right">{n(m?.saves)}</td>
                      <td className="num px-4 py-2.5 text-right">{n(m?.shares)}</td>
                      <td className="px-4 py-2.5 text-right">
                        {(r.permalink || m?.permalink) && (
                          <a href={r.permalink || m?.permalink} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()} aria-label="Open on Instagram" title="Open on Instagram"
                            className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-paper-line text-ink-soft hover:border-accent hover:text-accent">
                            <ExternalLink className="h-4 w-4" aria-hidden="true" />
                          </a>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        <Pager paged={paged} className="border-t border-paper-line px-4 py-3" />
      </section>
    </div>
  );
}
