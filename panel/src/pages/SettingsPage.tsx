import { useEffect, useState, type ReactNode } from 'react';
import { CheckCircle2, Github, Instagram, KeyRound, Link2, SlidersHorizontal, User, XCircle, type LucideIcon } from 'lucide-react';
import { cn } from '../admin/cn';
import type { Kind } from '../admin/api';
import { useAct, useAppState, useInstagram } from '../admin/hooks';
import { FormRow, INPUT, PageHeader, SELECT, Skeleton } from '../admin/ui';

function Card({ icon: Icon, title, hint, pill, children }: { icon: LucideIcon; title: string; hint: string; pill?: ReactNode; children: ReactNode }) {
  return (
    <section className="rounded-xl border border-paper-line bg-paper shadow-sm">
      <div className="flex items-center gap-3 border-b border-paper-line px-4 py-3">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent/[.12] text-accent"><Icon className="h-4 w-4" aria-hidden="true" /></span>
        <div className="min-w-0 flex-1">
          <h2 className="text-sm font-semibold">{title}</h2>
          <p className="text-xs text-ink-mute">{hint}</p>
        </div>
        {pill}
      </div>
      <div className="flex flex-col gap-4 p-4">{children}</div>
    </section>
  );
}

const Pill = ({ on, yes = 'Connected', no = 'Not connected' }: { on: boolean; yes?: string; no?: string }) => (
  <span className={cn('rounded-full px-2 py-0.5 text-xs font-semibold', on ? 'bg-ok-light text-ok' : 'bg-paper-alt text-ink-mute')}>{on ? yes : no}</span>
);

const ORDERS: { value: string; label: string; order: Kind[] }[] = [
  { value: 'ayah,tasbih', label: 'Ayah, then tasbih (alternate)', order: ['ayah', 'tasbih'] },
  { value: 'ayah', label: 'Ayah reels only', order: ['ayah'] },
  { value: 'tasbih', label: 'Tasbih reels only', order: ['tasbih'] },
];

export default function SettingsPage() {
  const state = useAppState();
  const s = state.data;
  const ig = useInstagram(Boolean(s?.instagram));
  const save = useAct('Saved');
  const [name, setName] = useState('');
  const [buffer, setBuffer] = useState(14);
  const [order, setOrder] = useState('ayah,tasbih');
  useEffect(() => {
    if (!s) return;
    setName(s.panel.name);
    setBuffer(s.config.buffer);
    setOrder(s.config.alternate.join(','));
  }, [s?.panel.name, s?.config.buffer, s?.config.alternate.join(',')]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="Settings" text="Your name in the console, how much is made and posted, and the accounts it uses." />
      {!s ? <Skeleton className="h-64" /> : (
        <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-2">
          <Card icon={User} title="Profile" hint="The name shown at the top right.">
            <form className="flex flex-col gap-4" onSubmit={(e) => { e.preventDefault(); save.mutate({ type: 'settings', settings: { panel: { name: name.trim() } } }); }}>
              <FormRow label="Full name"><input value={name} onChange={(e) => setName(e.target.value)} maxLength={60} className={INPUT} placeholder="Your name" /></FormRow>
              <button type="submit" disabled={save.isPending} className="h-10 w-fit cursor-pointer rounded-lg bg-accent px-4 text-sm font-semibold text-white hover:bg-accent-dark disabled:opacity-50">Save</button>
            </form>
          </Card>

          <Card icon={SlidersHorizontal} title="Automation" hint="What gets made every morning and posted at 09:00 / 19:00." pill={<Pill on={s.config.enabled} yes="On" no="Off" />}>
            <form className="flex flex-col gap-4" onSubmit={(e) => {
              e.preventDefault();
              save.mutate({ type: 'settings', settings: { config: { buffer, alternate: ORDERS.find((o) => o.value === order)!.order } } });
            }}>
              <div className="grid gap-4 sm:grid-cols-2">
                <FormRow label="Posting mix">
                  <select value={order} onChange={(e) => setOrder(e.target.value)} className={cn(SELECT, '!h-10 w-full')}>
                    {ORDERS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>
                </FormRow>
                <FormRow label="Keep ready" hint="Reels waiting (review + approved) before the daily maker stops. 14 = one week.">
                  <input type="number" min={2} max={60} value={buffer} onChange={(e) => setBuffer(Number(e.target.value))} className={INPUT} />
                </FormRow>
              </div>
              <button type="submit" disabled={save.isPending} className="h-10 w-fit cursor-pointer rounded-lg bg-accent px-4 text-sm font-semibold text-white hover:bg-accent-dark disabled:opacity-50">Save</button>
            </form>
          </Card>

          <Card icon={Link2} title="Connections" hint="Where reels are stored and where they are posted.">
            <div className="flex items-start gap-3">
              <Github className="mt-0.5 h-5 w-5 shrink-0 text-ink-soft" aria-hidden="true" />
              <div className="min-w-0 flex-1">
                <p className="flex items-center gap-2 font-medium">GitHub <Pill on /></p>
                <p className="text-xs text-ink-mute">Repo <a className="text-accent hover:underline" href={`https://github.com/${s.repo}`} target="_blank" rel="noreferrer">{s.repo}</a>: scripts, queue, and the workflows that make and post reels.</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Instagram className="mt-0.5 h-5 w-5 shrink-0 text-ink-soft" aria-hidden="true" />
              <div className="min-w-0 flex-1">
                <p className="flex items-center gap-2 font-medium">Instagram <Pill on={s.instagram && !ig.data?.error} no={s.instagram ? 'Error' : 'Not connected'} /></p>
                {s.instagram ? (
                  ig.data?.error ? <p className="flex items-center gap-1 text-xs text-danger"><XCircle className="h-3.5 w-3.5" aria-hidden="true" /> {ig.data.error}</p>
                    : <p className="flex items-center gap-1 text-xs text-ink-mute"><CheckCircle2 className="h-3.5 w-3.5 text-ok" aria-hidden="true" /> {ig.data?.profile ? `@${ig.data.profile.username} · ${ig.data.profile.followers_count} followers` : 'Checking…'}</p>
                ) : (
                  <ol className="mt-1 list-decimal space-y-1 ps-4 text-xs text-ink-soft">
                    <li>Create the Meta app and get the Instagram token (Instagram API with Instagram login).</li>
                    <li>GitHub repo → Settings → Secrets → Actions: add <code className="font-mono">IG_ACCESS_TOKEN</code> and <code className="font-mono">IG_USER_ID</code>, so posting works.</li>
                    <li>Vercel project → Settings → Environment Variables: add the same <code className="font-mono">IG_ACCESS_TOKEN</code>, then redeploy, so stats show here.</li>
                  </ol>
                )}
              </div>
            </div>
          </Card>

          <Card icon={KeyRound} title="Password" hint="One password protects this console.">
            <p className="text-sm text-ink-soft">The password is the <code className="font-mono text-xs">PANEL_PASSWORD</code> environment variable in Vercel. To change it, edit it there and redeploy. To sign out every device, also change <code className="font-mono text-xs">SESSION_SECRET</code>.</p>
            <p className="text-xs text-ink-mute">Sessions last 30 days. Wrong passwords are slowed down to stop guessing.</p>
          </Card>
        </div>
      )}
    </div>
  );
}
