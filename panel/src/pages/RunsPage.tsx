import { Activity, CheckCircle2, CircleDashed, ExternalLink, Loader2, RefreshCw, XCircle } from 'lucide-react';
import { cn } from '../admin/cn';
import type { Run } from '../admin/api';
import { useAppState } from '../admin/hooks';
import { ago, Badge, dateTime, Empty, PageHeader, Pager, Skeleton, usePaged } from '../admin/ui';

const EVENT: Record<string, string> = { schedule: 'scheduled', workflow_dispatch: 'manual', push: 'push' };

export function RunRow({ run }: { run: Run }) {
  const done = run.status === 'completed';
  const good = run.conclusion === 'success';
  const Icon = !done ? Loader2 : good ? CheckCircle2 : run.conclusion === 'skipped' || run.conclusion === 'cancelled' ? CircleDashed : XCircle;
  return (
    <li className="flex items-center gap-3 py-2.5">
      <Icon className={cn('h-4 w-4 shrink-0', !done && 'animate-spin text-accent', done && good && 'text-ok', done && !good && run.conclusion === 'failure' && 'text-danger', done && !good && run.conclusion !== 'failure' && 'text-ink-mute')} aria-hidden="true" />
      <span className="min-w-0 flex-1">
        <span className="block truncate font-medium">{run.name}</span>
        <span className="block truncate text-xs text-ink-mute">{run.title} · {EVENT[run.event] ?? run.event}</span>
      </span>
      {done && !good && <Badge tone={run.conclusion === 'failure' ? 'red' : 'slate'}>{run.conclusion}</Badge>}
      <span className="shrink-0 text-xs text-ink-mute" title={dateTime(run.created)}>{ago(run.created)}</span>
      <a href={run.url} target="_blank" rel="noreferrer" aria-label="Open run on GitHub" title="Open run on GitHub"
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-paper-line text-ink-soft hover:border-accent hover:text-accent">
        <ExternalLink className="h-4 w-4" aria-hidden="true" />
      </a>
    </li>
  );
}

export default function RunsPage() {
  const state = useAppState();
  const runs = state.data?.runs ?? [];
  const paged = usePaged(runs, null, 12);
  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Workflow runs"
        text="Every time GitHub made or posted reels. A red one means something needs a look; open it for the log."
        actions={
          <button type="button" onClick={() => void state.refetch()} className="flex h-9 cursor-pointer items-center gap-2 rounded-lg border border-paper-line bg-paper px-3 text-sm font-medium hover:bg-paper-alt">
            <RefreshCw className={cn('h-4 w-4', state.isFetching && 'animate-spin')} aria-hidden="true" /> Refresh
          </button>
        }
      />
      <section className="rounded-xl border border-paper-line bg-paper px-4 shadow-sm">
        {!state.data ? <div className="py-4"><Skeleton className="h-40" /></div> : runs.length === 0 ? <Empty icon={Activity} text="No runs yet." /> : (
          <ul className="divide-y divide-paper-line">{paged.items?.map((r) => <RunRow key={r.id} run={r} />)}</ul>
        )}
        <Pager paged={paged} className="border-t border-paper-line py-3" />
      </section>
    </div>
  );
}
