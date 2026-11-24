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

const shortcode = (link) => /instagram\.com\/(?:reel|p|tv)\/([^/?#]+)/.exec(link || '')?.[1] ?? null;
const HOUR = 3600_000;

/** Every post on the account, oldest first (follows paging, at most `max`). */
async function allMedia(user, max = 200) {
  const out = [];
  let page = await ig(`${user}/media`, {
    fields: 'id,caption,media_type,media_product_type,permalink,timestamp,like_count,comments_count,thumbnail_url,media_url',
    limit: '50',
  });
  for (;;) {
    out.push(...(page.data ?? []));
    const next = page.paging?.next;
    if (!next || out.length >= max) break;
    const r = await fetch(next);
    page = await r.json();
    if (!r.ok) break;
  }
  return out.reverse();
}

/** views / reach / saves / shares need the instagram_manage_insights permission; null when not allowed (yet). */
async function insights(id) {
  const ins = await ig(`${id}/insights`, { metric: 'views,reach,saved,shares,total_interactions' });
  const v = (n) => ins.data?.find((x) => x.name === n)?.values?.[0]?.value ?? null;
  return { views: v('views'), reach: v('reach'), saves: v('saved'), shares: v('shares'), interactions: v('total_interactions') };
}

/**
 * Account numbers, every post with its stats, and totals. Posts are matched to queue reels by media id, by link,
 * and for reels marked "posted by hand" without a link, by the closest post time (one post per reel).
 */
export default async function handler(req, res) {
  if (!guard(req, res)) return;
  if (!process.env.IG_ACCESS_TOKEN) return send(res, 200, { connected: false });
  try {
    const user = process.env.IG_USER_ID || 'me';
    const [profile, list, queue] = await Promise.all([
      ig(user, { fields: 'username,followers_count,media_count,profile_picture_url' }),
      allMedia(user),
      readJson('state/queue.json'),
    ]);

    let insightsError = null;
    const posts = await Promise.all(list.map(async (m) => {
      let st = { views: null, reach: null, saves: null, shares: null, interactions: null };
      try { st = await insights(m.id); } catch (e) { insightsError ??= e.message; }
      return {
        id: m.id, permalink: m.permalink, timestamp: m.timestamp, type: m.media_product_type || m.media_type,
        caption: m.caption ?? '', thumbnail: m.thumbnail_url || (m.media_type === 'IMAGE' ? m.media_url : null),
        likes: m.like_count ?? 0, comments: m.comments_count ?? 0, ...st, reel: null,
      };
    }));

    // match queue reels to posts
    const items = (queue.data?.items ?? []).filter((i) => i.status === 'posted');
    const byId = new Map(posts.map((p) => [p.id, p]));
    const byCode = new Map(posts.map((p) => [shortcode(p.permalink), p]));
    const take = (it, p) => { if (p && !p.reel) { p.reel = it.id; return true; } return false; };
    const left = [];
    for (const it of items) {
      if (!(take(it, byId.get(it.ig_media_id)) || take(it, byCode.get(shortcode(it.permalink))))) left.push(it);
    }
    for (const it of left) {  // hand-posted without a link: closest free post within 36 h, posted before it was marked
      const t = +new Date(it.posted ?? 0);
      let best = null;
      for (const p of posts) {
        if (p.reel || p.type !== 'REELS') continue;
        const d = t - +new Date(p.timestamp);
        if (d > -2 * HOUR && d < 36 * HOUR && (!best || Math.abs(d) < Math.abs(t - +new Date(best.timestamp)))) best = p;
      }
      take(it, best);
    }

    const media = {};
    for (const p of posts) if (p.reel) media[p.reel] = p;
    const sum = (k) => (posts.some((p) => p[k] != null) ? posts.reduce((n, p) => n + (p[k] ?? 0), 0) : null);
    const totals = {
      posts: posts.length, likes: sum('likes'), comments: sum('comments'), views: sum('views'),
      reach: sum('reach'), saves: sum('saves'), shares: sum('shares'),
    };
    send(res, 200, {
      connected: true, profile, media, posts: posts.slice().reverse(), totals,
      insights_error: insightsError && /permission/i.test(insightsError)
        ? 'Views, reach, saves and shares need the instagram_manage_insights permission on the Instagram token.'
        : insightsError,
    });
  } catch (e) {
    send(res, 200, { connected: true, error: e.message });
  }
}
