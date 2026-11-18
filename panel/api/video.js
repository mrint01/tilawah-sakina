import { ASSETS, guard, send } from './_lib.js';

// GitHub serves release files as downloads (application/octet-stream, no seeking), which iPhone
// Safari refuses to play. This serves them as real video with byte ranges:
//   ?id=…          the small preview (player in the panel)
//   ?id=…&full=1   the full-quality reel, for "Post manually". The panel fetches it in ≤3 MB ranges
//                  (Vercel caps one response at 4.5 MB) and joins them into one file on the phone.
const ID = /^\d{8}-\d{6}-(ayah|tasbih)$/;
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
