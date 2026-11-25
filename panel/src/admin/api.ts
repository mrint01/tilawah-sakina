export type Status = 'pending' | 'approved' | 'rejected' | 'posted' | 'failed';
export type Kind = 'ayah' | 'dua' | 'asma' | 'tasbih' | 'quiz';

export interface Reel {
  id: string;
  kind: Kind;
  title: string;
  caption: string;
  duration: number;
  size_mb?: number;
  mean_volume_db?: number;
  checks: Record<string, boolean>;
  status: Status;
  review: string | null;
  created: string;
  reviewed?: string;
  posted?: string;
  manual?: boolean;
  permalink?: string;
  ig_media_id?: string;
  reciter?: string;
  surah?: string;
  ref?: string;
  set?: string;
  /** dua: kind of dua (morning, after_salah, need, friday, arafah) and its Hisn al-Muslim id */
  category?: string;
  dua_id?: number;
  source?: string;
  /** asma: the name's number, 1-99 */
  number?: number;
  /** quiz: easy / medium / hard */
  level?: string;
  /** surah reels: nature theme of the video background, or "drawn" */
  background?: string;
}

export interface Run {
  id: number; name: string; event: string; status: string; conclusion: string | null; created: string; url: string; title: string;
}

/** Live render progress, written by pipeline.py into the release while a "Generate reels" run works. */
export interface MakeProgress {
  run_id: string; total: number; done: number; current: string;
  stage: 'starting' | 'rendering' | 'checking' | 'uploading' | 'done' | 'failed';
  frac: number; pct: number; finished: boolean; updated?: string; error?: string | null;
}

/** Live progress of a post, written by pipeline.py (posting.json in the release). */
export interface PostingProgress {
  run_id: string; id?: string; title?: string; started?: string; updated?: string;
  stage: 'preparing' | 'video' | 'hosting' | 'uploading' | 'processing' | 'publishing' | 'live' | 'failed';
  pct: number; finished: boolean; permalink?: string; error?: string;
}

/** One reel to make, from the "Make reels" popup. No surah = a curated passage; no reciter/set = picked for you. */
export type MakeJob =
  | { kind: 'ayah'; surah?: number; ayah?: number; reciter?: string }
  | { kind: 'dua'; category?: string }
  | { kind: 'asma'; number?: number; reciter?: string }
  | { kind: 'tasbih'; set?: string }
  | { kind: 'quiz'; level?: string };

/** Reels posted again every week (Friday Al-Kahf parts). Same fields as a reel where it matters. */
export interface WeeklyReel {
  id: string; title: string; caption: string; file: string; day: string; time: string; cron: string;
  duration: number; size_mb: number; surah?: string; reciter?: string; kind: Kind;
}
export interface WeeklyState { assets: string; items: WeeklyReel[]; posted: { id: string; at: string; permalink?: string }[] }

export interface PanelState {
  repo: string;
  assets: string;
  items: Reel[];
  config: { enabled: boolean; buffer_days: number; reciters: Record<string, string> };
  panel: { name: string };
  instagram: boolean;
  runs: Run[];
  progress: MakeProgress | null;
  posting: PostingProgress | null;
  weekly: WeeklyState;
}

/** One post on the Instagram account with its numbers. views/reach/saves/shares are null without the insights permission. */
export interface MediaStats {
  id?: string; permalink?: string; timestamp?: string; type?: string; caption?: string; thumbnail?: string | null; reel?: string | null;
  likes: number; comments: number; views: number | null; reach: number | null; saves: number | null; shares: number | null;
  /** average watch time of a reel, seconds */
  watch?: number | null; reposts?: number | null;
  /** % of viewers who swiped away in the first seconds */
  skip?: number | null; error?: string;
}
export interface IgTotals { posts: number; likes: number | null; comments: number | null; views: number | null; reach: number | null; saves: number | null; shares: number | null; reposts?: number | null }
export interface InstagramStats {
  connected: boolean;
  error?: string;
  /** set when the token can't read views/reach/saves/shares */
  insights_error?: string | null;
  profile?: { username: string; followers_count: number; media_count: number; profile_picture_url?: string };
  /** queue reel id -> its post */
  media?: Record<string, MediaStats>;
  /** every post on the account, newest first */
  posts?: MediaStats[];
  totals?: IgTotals;
}

export class SignedOut extends Error {}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, { credentials: 'same-origin', ...init, headers: { 'content-type': 'application/json', ...init?.headers } });
  const data = await r.json().catch(() => ({}));
  if (r.status === 401 && data.error === 'signed_out') throw new SignedOut('signed out');
  if (!r.ok) throw new Error(data.error || `Request failed (${r.status})`);
  return data as T;
}

export type Action =
  | { type: 'approve'; id: string; note?: string }
  | { type: 'reject'; id: string; note: string }
  | { type: 'requeue'; id: string }
  | { type: 'mark_posted'; id: string; permalink?: string }
  | { type: 'unmark_posted'; id: string }
  | { type: 'toggle'; enabled: boolean }
  | { type: 'settings'; settings: { config?: { buffer_days?: number; reciters?: Record<string, string> }; panel?: { name: string } } }
  | { type: 'post_now'; kind?: Kind; id?: string }
  | { type: 'generate'; ayah?: number; tasbih?: number; jobs?: MakeJob[] };

export const api = {
  state: () => call<PanelState>('/api/state'),
  instagram: () => call<InstagramStats>('/api/instagram'),
  login: (password: string) => call<{ ok: true }>('/api/login', { method: 'POST', body: JSON.stringify({ password }) }),
  logout: () => call<{ ok: true }>('/api/login', { method: 'DELETE' }),
  act: (a: Action) => call<{ ok: true }>('/api/action', { method: 'POST', body: JSON.stringify(a) }),
};

export const asset = (s: PanelState, id: string, ext: 'mp4' | 'png') => `${s.assets}${id}.${ext}`;

/** Full-quality reel as a File, fetched in ranges through /api/video (one Vercel response is capped at 4.5 MB). */
export async function fetchFullVideo(id: string, onProgress?: (done: number) => void): Promise<File> {
  const CHUNK = 3_000_000;
  const parts: ArrayBuffer[] = [];
  let start = 0;
  let size = Infinity;
  while (start < size) {
    const r = await fetch(`/api/video?id=${encodeURIComponent(id)}&full=1`, {
      credentials: 'same-origin',
      headers: { Range: `bytes=${start}-${start + CHUNK - 1}` },
    });
    if (r.status === 401) throw new SignedOut('signed out');
    if (r.status !== 206) {
      const data = await r.json().catch(() => ({}));
      throw new Error(data.error || `Download failed (${r.status})`);
    }
    const m = /bytes (\d+)-(\d+)\/(\d+)/.exec(r.headers.get('content-range') || '');
    if (!m) throw new Error('Download failed (no range)');
    size = Number(m[3]);
    parts.push(await r.arrayBuffer());
    start = Number(m[2]) + 1;
    onProgress?.(start / size);
  }
  return new File(parts, `tilawah-sakina-${id}.mp4`, { type: 'video/mp4' });
}

/** The daily plan (Tunisia time, UTC+1). The same as pipeline.py SLOTS and the crons in post.yml / generate.yml. */
export const SLOTS: { time: string; utcHour: number; kind: Kind; label: string }[] = [
  { time: '00:00', utcHour: 23, kind: 'ayah', label: 'Surah' },
  { time: '06:00', utcHour: 5, kind: 'dua', label: 'Dua' },
  { time: '12:00', utcHour: 11, kind: 'asma', label: 'Asma al-Husna' },
  { time: '18:00', utcHour: 17, kind: 'tasbih', label: 'Tasbih' },
  { time: '21:00', utcHour: 20, kind: 'quiz', label: 'Quiz' },
];
export const MAKE_TIME = '03:00';
export const REVIEW_TIME = '04:30';
/** The 06:00 dua by weekday (0 = Sunday, as Date.getDay()). Same as DUA_BY_WEEKDAY in pipeline.py. */
export const DUA_BY_DAY = ['after_salah', 'morning', 'need', 'morning', 'after_salah', 'friday', 'morning'];
export const DUA_LABEL: Record<string, string> = {
  morning: 'Morning adhkar', after_salah: 'Dua after salah', need: 'Dua for a need', friday: 'Salawat & Friday', arafah: 'Day of Arafah',
};

export interface Upcoming { at: Date; kind: Kind; label: string; reel: Reel | null }

/** The next n posting slots and the approved reel each one will post (null = nothing approved of that kind). */
export function upcoming(items: Reel[], n: number, from = new Date()): Upcoming[] {
  const left = items.filter((i) => i.status === 'approved');
  const take = (kind: Kind, day: Date) => {
    let pool = left.filter((r) => r.kind === kind);
    if (kind === 'asma') pool.sort((x, y) => (x.number ?? 0) - (y.number ?? 0));
    if (kind === 'dua') {
      pool = pool.filter((r) => r.category !== 'arafah');
      const tunis = new Date(day.getTime() + 3600_000);
      const want = DUA_BY_DAY[tunis.getUTCDay()];
      pool = [...pool.filter((r) => r.category === want), ...pool.filter((r) => r.category !== want)];
    }
    const r = pool[0] ?? null;
    if (r) left.splice(left.indexOf(r), 1);
    return r;
  };
  const out: Upcoming[] = [];
  const d = new Date(Date.UTC(from.getUTCFullYear(), from.getUTCMonth(), from.getUTCDate() - 1));
  while (out.length < n) {
    for (const sl of [...SLOTS].sort((x, y) => x.utcHour - y.utcHour)) {
      const t = new Date(d.getTime() + sl.utcHour * 3600_000);
      if (t > from && out.length < n) out.push({ at: t, kind: sl.kind, label: sl.label, reel: take(sl.kind, t) });
    }
    d.setUTCDate(d.getUTCDate() + 1);
  }
  return out;
}

const slotFmt = new Intl.DateTimeFormat('en-GB', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'Africa/Tunis' });
export const slot = (d: Date) => slotFmt.format(d);

export const CHECK_LABEL: Record<string, string> = {
  size_1080x1920: '1080×1920 vertical',
  video_h264: 'H.264 video',
  audio_aac: 'AAC audio',
  length_60_90s: 'Length 60–90 s',
  length_whole_surah: 'Whole surah, up to 90 s',
  length_60s: 'Length 60 s',
  length_up_to_3min: 'Length up to 3 min',
  length_10_60s: 'Length 10–60 s',
  length_8_75s: 'Length 8–75 s',
  length_50_150s: 'Length 50–150 s',
  audio_not_silent: 'Audio not silent',
  file_under_100mb: 'File under 100 MB',
};
