import { useState } from 'react';
import { Loader2, Sparkles, TriangleAlert } from 'lucide-react';
import { cn } from './cn';
import { DUA_LABEL, type Kind, type MakeJob, type PanelState } from './api';
import { KIND, makingRun, useAct } from './hooks';
import { SURAHS } from './surahs';
import { FormRow, INPUT, Modal } from './ui';

export const TASBIH_SETS: [string, string][] = [
  ['subhanallah', 'SubhanAllah'], ['alhamdulillah', 'Alhamdulillah'], ['allahuakbar', 'Allahu Akbar'],
  ['wabihamdihi', 'SubhanAllahi wa bihamdihi'], ['astaghfirullah', 'Astaghfirullah'],
  ['tahlil', 'La ilaha illallah'], ['salawat', 'Salawat upon the Prophet ﷺ'],
];
const FIELD = INPUT + ' cursor-pointer';
const KINDS: Kind[] = ['ayah', 'dua', 'asma', 'tasbih', 'quiz'];

/** "Make reels" button + popup: surah (surah, start ayah, reciter), dua (kind of dua), Asma al-Husna (which name),
 *  tasbih (dhikr) or quiz (level), and how many. */
export function MakeReelsButton({ busy, reciters }: { busy: boolean; reciters: string[] }) {
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState<Kind>('ayah');
  const [category, setCategory] = useState('');
  const [nameNo, setNameNo] = useState('');
  const [level, setLevel] = useState('');
  const [surah, setSurah] = useState('');
  const [ayah, setAyah] = useState('');
  const [reciter, setReciter] = useState('');
  const [set, setSet] = useState('');
  const [count, setCount] = useState(1);
  const act = useAct(() => 'Started: watch the progress bar on this page');

  const info = SURAHS.find(([n]) => String(n) === surah);
  const ayahNum = Number(ayah);
  const ayahBad = ayah !== '' && (!Number.isInteger(ayahNum) || ayahNum < 1 || (info ? ayahNum > info[4] : true));

  const submit = () => {
    const job: MakeJob =
      kind === 'tasbih' ? { kind, ...(set ? { set } : {}) }
      : kind === 'dua' ? { kind, ...(category ? { category } : {}) }
      : kind === 'asma' ? { kind, ...(nameNo ? { number: Number(nameNo) } : {}), ...(reciter ? { reciter } : {}) }
      : kind === 'quiz' ? { kind, ...(level ? { level } : {}) }
      : { kind, ...(surah ? { surah: Number(surah) } : {}), ...(surah && ayah ? { ayah: ayahNum } : {}), ...(reciter ? { reciter } : {}) };
    // a start ayah / a chosen name applies to the first reel; the others pick on their own
    const jobs: MakeJob[] = Array.from({ length: count }, (_, i) =>
      i > 0 && job.kind === 'ayah' && job.ayah ? { ...job, ayah: undefined }
        : i > 0 && job.kind === 'asma' && job.number ? { ...job, number: ((job.number + i - 1) % 99) + 1 } : job);
    act.mutate({ type: 'generate', jobs }, { onSuccess: () => setOpen(false) });
  };

  return (
    <>
      <button type="button" onClick={() => setOpen(true)} disabled={busy}
        title={busy ? 'Reels are being made right now' : undefined}
        className="flex h-9 cursor-pointer items-center gap-2 rounded-lg border border-paper-line bg-paper px-3 text-sm font-medium hover:bg-paper-alt disabled:cursor-default disabled:opacity-50">
        <Sparkles className="h-4 w-4" aria-hidden="true" /> Make reels
      </button>
      <Modal open={open} onClose={() => setOpen(false)} title="Make reels" icon={Sparkles} wide
        text="They render on GitHub (about 2 minutes each), then wait in Review for Claude and you.">
        <div role="radiogroup" aria-label="Type" className="grid grid-cols-2 gap-2 sm:grid-cols-5">
          {KINDS.map((k) => {
            const Icon = KIND[k].icon;
            return (
              <button key={k} type="button" role="radio" aria-checked={kind === k} onClick={() => setKind(k)}
                className={cn('flex h-11 cursor-pointer items-center justify-center gap-2 rounded-lg border px-2 text-sm font-medium',
                  kind === k ? 'border-accent bg-accent/10 text-accent' : 'border-paper-line text-ink-soft hover:bg-paper-alt')}>
                <Icon className="h-4 w-4 shrink-0" aria-hidden="true" /> <span className="truncate">{KIND[k].label}</span>
              </button>
            );
          })}
        </div>

        {kind === 'ayah' ? (
          <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_7rem]">
            <FormRow label="Surah" hint={info ? `${info[3]} · ${info[4]} ayahs` : 'Any: one of the hand-picked passages'}>
              <select value={surah} onChange={(e) => { setSurah(e.target.value); setAyah(''); }} className={FIELD}>
                <option value="">Any surah (hand-picked passages)</option>
                {SURAHS.map(([n, name, ar]) => <option key={n} value={n}>{n}. {name} · {ar}</option>)}
              </select>
            </FormRow>
            <FormRow label="From ayah" hint={surah ? 'Empty = random' : 'Pick a surah first'}
              error={ayahBad ? `1 to ${info?.[4] ?? '…'}` : undefined}>
              <input type="number" inputMode="numeric" min={1} max={info?.[4]} value={ayah} disabled={!surah}
                onChange={(e) => setAyah(e.target.value)} placeholder="Random" className={cn(INPUT, 'disabled:opacity-50')} />
            </FormRow>
            <div className="sm:col-span-2">
              <FormRow label="Reciter">
                <select value={reciter} onChange={(e) => setReciter(e.target.value)} className={FIELD}>
                  <option value="">Random reciter</option>
                  {reciters.map((r) => <option key={r} value={r}>{r}</option>)}
                </select>
              </FormRow>
            </div>
          </div>
        ) : kind === 'dua' ? (
          <FormRow label="Kind of dua" hint="Text and recitation from Hisn al-Muslim. The Arafah dua only posts on the Day of Arafah.">
            <select value={category} onChange={(e) => setCategory(e.target.value)} className={FIELD}>
              <option value="">What the coming days need</option>
              {Object.entries(DUA_LABEL).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
            </select>
          </FormRow>
        ) : kind === 'asma' ? (
          <div className="grid gap-3 sm:grid-cols-2">
            <FormRow label="Name" hint="The series posts 1 → 99 in order.">
              <select value={nameNo} onChange={(e) => setNameNo(e.target.value)} className={FIELD}>
                <option value="">Next in the series</option>
                {Array.from({ length: 99 }, (_, i) => <option key={i + 1} value={i + 1}>Name {i + 1} of 99</option>)}
              </select>
            </FormRow>
            <FormRow label="Reciter (the ayah)">
              <select value={reciter} onChange={(e) => setReciter(e.target.value)} className={FIELD}>
                <option value="">Random reciter</option>
                {reciters.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </FormRow>
          </div>
        ) : kind === 'quiz' ? (
          <FormRow label="Level" hint="Easy: Juz Amma. Medium: well-known surahs. Hard: any surah.">
            <select value={level} onChange={(e) => setLevel(e.target.value)} className={FIELD}>
              <option value="">Mixed (mostly easy)</option>
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </FormRow>
        ) : (
          <FormRow label="Dhikr" hint="Each tasbih reel is one minute: 33 counts down to 0, with the Kaaba.">
            <select value={set} onChange={(e) => setSet(e.target.value)} className={FIELD}>
              <option value="">Least used so far</option>
              {TASBIH_SETS.map(([k, label]) => <option key={k} value={k}>33× {label}</option>)}
            </select>
          </FormRow>
        )}

        <FormRow label="How many" hint={kind === 'ayah' && ayah && count > 1 ? 'The first starts at your ayah, the others pick other passages of the surah.' : undefined}>
          <select value={count} onChange={(e) => setCount(Number(e.target.value))} className={FIELD}>
            {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n} reel{n > 1 ? 's' : ''}</option>)}
          </select>
        </FormRow>

        <div className="flex flex-wrap justify-end gap-2 pt-1">
          <button type="button" onClick={() => setOpen(false)}
            className="h-10 cursor-pointer rounded-lg border border-paper-line px-4 text-sm font-medium text-ink-soft hover:bg-paper-alt">Cancel</button>
          <button type="button" onClick={submit} disabled={ayahBad || act.isPending}
            className="flex h-10 cursor-pointer items-center gap-2 rounded-lg bg-accent px-4 text-sm font-semibold text-white hover:bg-accent-dark disabled:cursor-default disabled:opacity-50">
            {act.isPending && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />} Make {count} reel{count > 1 ? 's' : ''}
          </button>
        </div>
      </Modal>
    </>
  );
}

/** Progress card while a "Generate reels" run is queued or working (and for a few minutes after a local render). */
export function MakeProgressCard({ s }: { s: PanelState }) {
  const run = makingRun(s);
  const p = s.progress;
  const fresh = p?.updated ? Date.now() - new Date(p.updated).getTime() < 90_000 : false;
  const mine = p && (run ? p.run_id === String(run.id) : p.run_id === 'local' && fresh && !p.finished);
  if (!run && !mine) return null;

  let title = 'Waiting for GitHub to start…';
  let detail = 'GitHub usually starts within a minute.';
  let pct: number | null = null;
  if (p && mine && !p.finished) {
    const stage = { starting: 'Starting', rendering: 'Rendering', checking: 'Checking', uploading: 'Uploading', done: 'Done', failed: 'Failed' }[p.stage];
    title = `Making reel ${Math.min(p.done + 1, p.total)} of ${p.total}`;
    detail = `${stage}${p.current ? `: ${p.current}` : ''}`;
    pct = p.pct;
  } else if (p && mine && p.finished) {
    title = p.stage === 'failed' ? 'Making reels failed' : 'Saving to the review queue…';
    detail = p.stage === 'failed' ? (p.error || 'See the run on GitHub.') : `${p.total} reel${p.total > 1 ? 's' : ''} made. They show in Review in a moment.`;
    pct = p.stage === 'failed' ? null : 100;
  } else if (run?.status === 'in_progress') {
    title = 'Setting up…';
    detail = 'Installing the video tools (about 1 minute).';
  }
  const failed = p && mine && p.stage === 'failed';

  return (
    <section aria-live="polite" className="rounded-xl border border-paper-line bg-paper p-4 shadow-sm">
      <div className="flex items-start gap-3">
        <span className={cn('flex h-9 w-9 shrink-0 items-center justify-center rounded-lg', failed ? 'bg-danger-light text-danger' : 'bg-accent/10 text-accent')}>
          {failed ? <TriangleAlert className="h-4 w-4" aria-hidden="true" /> : <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline justify-between gap-3">
            <h2 className="text-sm font-semibold">{title}</h2>
            {pct !== null && <span className="num text-sm font-semibold text-accent">{pct}%</span>}
          </div>
          <p className="truncate text-xs text-ink-mute">{detail}</p>
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-paper-alt" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct ?? undefined}>
            {pct === null
              ? <div className={cn('h-full w-1/3 rounded-full', failed ? 'bg-danger' : 'animate-pulse bg-accent/50')} />
              : <div className="h-full rounded-full bg-accent transition-[width] duration-700" style={{ width: `${Math.max(2, pct)}%` }} />}
          </div>
          {run && <a href={run.url} target="_blank" rel="noreferrer" className="mt-1.5 inline-block text-xs text-ink-mute underline hover:text-accent">Open the run on GitHub</a>}
        </div>
      </div>
    </section>
  );
}
