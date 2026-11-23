import { guard, readJson, send } from './_lib.js';

// Instagram Login tokens ("IG...") use graph.instagram.com; Facebook / system-user tokens ("EAA...") use graph.facebook.com
const GRAPH = (process.env.IG_ACCESS_TOKEN || '').startsWith('EAA')
  ? 'https://graph.facebook.com/v22.0' : 'https://graph.instagram.com/v22.0';

async function ig(path, params = {}) {
  const qs = new URLSearchParams({ ...params, access_token: process.env.IG_ACCESS_TOKEN });
  const r = await fetch(`${GRAPH}/${path}?${qs}`);
  const data = await r.json();
  if (!r.ok) throw new Error(data?.error?.message || `Instagram ${r.status}`);
  return data;
}

/** Account numbers + per-reel views/likes. Works once IG_ACCESS_TOKEN is set; until then { connected: false }. */
export default async function handler(req, res) {
  if (!guard(req, res)) return;
  if (!process.env.IG_ACCESS_TOKEN) return send(res, 200, { connected: false });
  try {
    const profile = await ig(process.env.IG_USER_ID || 'me', { fields: 'username,followers_count,media_count' });
    const { data } = await readJson('state/queue.json');
    const posted = (data?.items ?? []).filter((i) => i.status === 'posted' && i.ig_media_id).slice(-40);
    const media = {};
    await Promise.all(posted.map(async (p) => {
      try {
        const m = await ig(p.ig_media_id, { fields: 'like_count,comments_count,permalink' });
        let views = null, saves = null, shares = null, reach = null;
        try {
          const ins = await ig(`${p.ig_media_id}/insights`, { metric: 'views,reach,saved,shares' });
          const v = (n) => ins.data?.find((x) => x.name === n)?.values?.[0]?.value ?? null;
          views = v('views'); reach = v('reach'); saves = v('saved'); shares = v('shares');
        } catch { /* insights can lag a few minutes after posting */ }
        media[p.id] = { likes: m.like_count ?? 0, comments: m.comments_count ?? 0, permalink: m.permalink, views, reach, saves, shares };
      } catch (e) {
        media[p.id] = { error: e.message };
      }
    }));
    send(res, 200, { connected: true, profile, media });
  } catch (e) {
    send(res, 200, { connected: true, error: e.message });
  }
}
