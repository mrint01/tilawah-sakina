import { useState } from 'react';
import { Send, Trash2 } from 'lucide-react';
import type { PanelState, Reel } from './api';
import { postingRun, useAct } from './hooks';
import { Modal } from './ui';

/** "Publish now" and "Remove" for one approved reel, each with its confirmation (used on the reel page). */
export function ReelActions({ s, r, onDone }: { s: PanelState; r: Reel; onDone?: () => void }) {
  const act = useAct((a) => (a.type === 'post_now' ? 'Publishing started: follow it at the top of the page' : 'Removed: it will not be posted'));
  const [ask, setAsk] = useState<'publish' | 'remove' | null>(null);
  const busy = Boolean(postingRun(s));
  return (
    <>
      <div className="flex flex-wrap gap-2">
        <button type="button" disabled={busy || !s.instagram || act.isPending} onClick={() => setAsk('publish')}
          title={busy ? 'A post is already being published' : !s.instagram ? 'Connect Instagram first' : 'Publish this reel on Instagram now'}
          className="flex h-9 cursor-pointer items-center gap-2 rounded-lg bg-accent px-3 text-sm font-semibold text-white hover:bg-accent-dark disabled:cursor-default disabled:opacity-40">
          <Send className="h-4 w-4" aria-hidden="true" /> Publish now
        </button>
        <button type="button" disabled={act.isPending} onClick={() => setAsk('remove')}
          className="flex h-9 cursor-pointer items-center gap-2 rounded-lg border border-danger/50 px-3 text-sm font-medium text-danger hover:bg-danger-light disabled:opacity-50">
          <Trash2 className="h-4 w-4" aria-hidden="true" /> Remove
        </button>
      </div>

      <Modal open={ask === 'publish'} onClose={() => setAsk(null)} title="Publish this reel now?" icon={Send}
        text="It goes to Instagram right away with its caption and cover. Follow the progress at the top of the page until it is live.">
        <p className="text-sm font-semibold">{r.title}</p>
        <p className="max-h-40 overflow-y-auto whitespace-pre-wrap rounded-lg border border-paper-line bg-paper-alt p-3 text-xs text-ink-soft">{r.caption}</p>
        <div className="flex justify-end gap-2 pt-1">
          <button type="button" autoFocus onClick={() => setAsk(null)}
            className="h-10 cursor-pointer rounded-lg border border-paper-line px-4 text-sm font-medium text-ink-soft hover:bg-paper-alt">Cancel</button>
          <button type="button" disabled={act.isPending || busy}
            onClick={() => act.mutate({ type: 'post_now', id: r.id }, { onSuccess: () => { setAsk(null); window.scrollTo({ top: 0, behavior: 'smooth' }); onDone?.(); } })}
            className="flex h-10 cursor-pointer items-center gap-2 rounded-lg bg-accent px-4 text-sm font-semibold text-white hover:bg-accent-dark disabled:opacity-50">
            <Send className="h-4 w-4" aria-hidden="true" /> Publish now
          </button>
        </div>
      </Modal>

      <Modal open={ask === 'remove'} onClose={() => setAsk(null)} title="Remove this reel?" icon={Trash2} tone="danger"
        text="It will not be posted. Its video file is deleted from GitHub at the next posting run; the next approved reel of the same type takes its slot.">
        <p className="text-sm font-semibold">{r.title}</p>
        <div className="flex justify-end gap-2 pt-1">
          <button type="button" autoFocus onClick={() => setAsk(null)}
            className="h-10 cursor-pointer rounded-lg border border-paper-line px-4 text-sm font-medium text-ink-soft hover:bg-paper-alt">Cancel</button>
          <button type="button" disabled={act.isPending}
            onClick={() => act.mutate({ type: 'reject', id: r.id, note: 'Removed from the reel page in the panel' }, { onSuccess: () => { setAsk(null); onDone?.(); } })}
            className="flex h-10 cursor-pointer items-center gap-2 rounded-lg bg-danger px-4 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50">
            <Trash2 className="h-4 w-4" aria-hidden="true" /> Remove
          </button>
        </div>
      </Modal>
    </>
  );
}
