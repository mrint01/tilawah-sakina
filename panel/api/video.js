import { ASSETS, guard, send } from './_lib.js';

// GitHub serves release files as downloads (application/octet-stream, no seeking), which iPhone
// Safari refuses to play. This serves the small preview copy as a real video with byte ranges.
const ID = /^\d{8}-\d{6}-(ayah|tasbih)$/;
const cache = new Map(); // warm function instances keep the last few previews in memory

async function load(id) {
  if (cache.has(id)) return cache.get(id);
  const r = await fetch(`${ASSETS}${id}-preview.mp4`, { redirect: 'follow' });
  if (!r.ok) return null;
  const buf = Buffer.from(await r.arrayBuffer());
  cache.set(id, buf);
  if (cache.size > 6) cache.delete(cache.keys().next().value);
  return buf;
}

export default async function handler(req, res) {
  if (!guard(req, res)) return;
  const id = new URL(req.url, 'http://x').searchParams.get('id') || '';
  if (!ID.test(id)) return send(res, 400, { error: 'bad id' });
  const buf = await load(id);
  if (!buf) return send(res, 404, { error: 'No preview for this reel yet.' });

  const size = buf.length;
  res.setHeader('content-type', 'video/mp4');
  res.setHeader('accept-ranges', 'bytes');
  res.setHeader('cache-control', 'private, max-age=86400');
  const m = /^bytes=(\d*)-(\d*)$/.exec(req.headers.range || '');
  if (!m) {
    res.statusCode = 200;
    res.setHeader('content-length', size);
    return res.end(req.method === 'HEAD' ? undefined : buf);
  }
  let start = m[1] === '' ? size - Number(m[2]) : Number(m[1]);
  let end = m[1] === '' || m[2] === '' ? size - 1 : Number(m[2]);
  start = Math.max(0, start);
  end = Math.min(end, size - 1);
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
