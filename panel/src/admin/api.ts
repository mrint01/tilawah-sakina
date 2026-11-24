export type Status = 'pending' | 'approved' | 'rejected' | 'posted' | 'failed';
export type Kind = 'ayah' | 'tasbih';

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

/** One reel to make, from the "Make reels" popup. No surah = a curated passage; no reciter/set = picked for you. */
export type MakeJob =
  | { kind: 'ayah'; surah?: number; ayah?: number; reciter?: string }
  | { kind: 'tasbih'; set?: string };

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
  config: { enabled: boolean; alternate: Kind[]; buffer: number; reciters: Record<string, string> };
  panel: { name: string };
  instagram: boolean;
  runs: Run[];
  progress: MakeProgress | null;
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
  | { type: 'settings'; settings: { config?: { alternate?: Kind[]; buffer?: number; reciters?: Record<string, string> }; panel?: { name: string } } }
  | { type: 'post_now' }
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

/** Same order the posting workflow uses: alternate kinds, oldest approved first within a kind. */
export function postingOrder(items: Reel[], alternate: Kind[]): Reel[] {
  const approved = items.filter((i) => i.status === 'approved');
  const posted = items.filter((i) => i.status === 'posted');
  const order = alternate.length ? alternate : (['ayah', 'tasbih'] as Kind[]);
  let last = posted.at(-1)?.kind;
  const out: Reel[] = [];
  const left = [...approved];
  while (left.length) {
    const want = last && order.includes(last) ? order[(order.indexOf(last) + 1) % order.length] : order[0];
    const i = Math.max(0, left.findIndex((x) => x.kind === want));
    const [it] = left.splice(i, 1);
    out.push(it);
    last = it.kind;
  }
  return out;
}

/** Next slots of the posting schedule: 08:00 and 18:00 UTC (09:00 / 19:00 Tunisia). */
export function nextSlots(n: number, from = new Date()): Date[] {
  const out: Date[] = [];
  const d = new Date(Date.UTC(from.getUTCFullYear(), from.getUTCMonth(), from.getUTCDate()));
  while (out.length < n) {
    for (const h of [8, 18]) {
      const t = new Date(d.getTime() + h * 3600_000);
      if (t > from && out.length < n) out.push(t);
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
  audio_not_silent: 'Audio not silent',
  file_under_100mb: 'File under 100 MB',
};
