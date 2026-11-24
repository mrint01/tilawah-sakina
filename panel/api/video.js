import { ASSETS, REPO, guard, send } from './_lib.js';

// GitHub serves release files as downloads (application/octet-stream, no seeking), which iPhone
// Safari refuses to play. This serves them as real video with byte ranges:
//   ?id=…          the small preview (player in the panel)
//   ?id=…&full=1   the full-quality reel, for "Post manually". The panel fetches it in ≤3 MB ranges
//                  (Vercel caps one response at 4.5 MB) and joins them into one file on the phone.
const ID = /^\d{8}-\d{6}-(ayah|tasbih|dua|asma|quiz)$/;
// Weekly reels (Friday Al-Kahf, ~12 min, ~38 MB) live in the 'weekly' release. Too big to hold in memory:
// every range is fetched from GitHub as a range and passed on. They have no separate preview.
const WEEKLY_ID = /^kahf-part[12]$/;
const WEEKLY = `https://github.com/${REPO}/releases/download/weekly/`;

async function weekly(req, res, id) {
  const m = /^bytes=(\d*)-(\d*)$/.exec(req.headers.range || '');
  if (!m) { // plain request (download link): let GitHub send the whole file
    res.statusCode = 302;
    res.setHeader('location', `${WEEKLY}${id}.mp4`);
    return res.end();
  }
  let range = req.headers.range;
  if (m[1] !== '') { // cap open or long ranges to one Vercel-sized chunk
    const start = Number(m[1]);
    const end = m[2] === '' ? start + MAX_CHUNK - 1 : Math.min(Number(m[2]), start + MAX_CHUNK - 1);
    range = `bytes=${start}-${end}`;
  }
  const r = await fetch(`${WEEKLY}${id}.mp4`, { headers: { range }, redirect: 'follow' });
  if (r.status !== 206) return send(res, r.status === 416 ? 416 : 502, { error: 'Could not read the video from GitHub.' });
  res.statusCode = 206;
  res.setHeader('content-type', 'video/mp4');
  res.setHeader('accept-ranges', 'bytes');
  res.setHeader('cache-control', 'private, max-age=86400');
  res.setHeader('content-range', r.headers.get('content-range'));
  const buf = Buffer.from(await r.arrayBuffer());
  res.setHeader('content-length', buf.length);
  res.end(req.method === 'HEAD' ? undefined : buf);
}
const MAX_CHUNK = 3_500_000;
const cache = new Map(); // warm function instances keep the last few files in memory

async function load(name) {
  if (cache.has(name)) return cache.get(name);
  const r = await fetch(`${ASSETS}${name}`, { redirect: 'follow' });
  if (!r.ok) return null;
  const buf = Buffer.from(await r.arrayBuffer());
  cache.set(name, buf);
  if (cache.size > 6) cache.delete(cache.keys().next().value);
  return buf;
}

export default async function handler(req, res) {
  if (!guard(req, res)) return;
  const url = new URL(req.url, 'http://x');
  const id = url.searchParams.get('id') || '';
  const full = url.searchParams.get('full') === '1';
  if (WEEKLY_ID.test(id)) return weekly(req, res, id);
  if (!ID.test(id)) return send(res, 400, { error: 'bad id' });
  const name = full ? `${id}.mp4` : `${id}-preview.mp4`;
  const m = /^bytes=(\d*)-(\d*)$/.exec(req.headers.range || '');

  // A plain request for the full file would be too big for one response: send the browser to GitHub.
  if (full && !m) {
    res.statusCode = 302;
    res.setHeader('location', `${ASSETS}${name}`);
    return res.end();
  }

  const buf = await load(name);
  if (!buf) return send(res, 404, { error: full ? 'This video was already removed (posted).' : 'No preview for this reel yet.' });

  const size = buf.length;
  res.setHeader('content-type', 'video/mp4');
  res.setHeader('accept-ranges', 'bytes');
  res.setHeader('cache-control', 'private, max-age=86400');
  if (!m) {
    res.statusCode = 200;
    res.setHeader('content-length', size);
    return res.end(req.method === 'HEAD' ? undefined : buf);
  }
  let start = m[1] === '' ? size - Number(m[2]) : Number(m[1]);
  let end = m[1] === '' || m[2] === '' ? size - 1 : Number(m[2]);
  start = Math.max(0, start);
  end = Math.min(end, size - 1, start + MAX_CHUNK - 1);
  if (start > end) {
    res.statusCode = 416;
    res.setHeader('content-range', `bytes */${size}`);
    return res.end();
  }
  res.statusCode = 206;
  res.setHeader('content-range', `bytes ${start}-${end}/${size}`);
  res.setHeader('content-length', end - start + 1);
  res.end(req.method === 'HEAD' ? undefined : buf.subarray(start, end + 1));
}
