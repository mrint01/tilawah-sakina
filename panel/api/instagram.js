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
/** First 80 letters/digits of a caption, lower case: the same text however emoji or spacing changed. */
const key = (t) => (t || '').toLowerCase().normalize('NFKD').replace(/[^\p{L}\p{N}]+/gu, '').slice(0, 80);

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
async function insights(id, isReel) {
  const metric = 'views,reach,saved,shares,total_interactions' + (isReel ? ',ig_reels_avg_watch_time,reposts,reels_skip_rate' : '');
  const ins = await ig(`${id}/insights`, { metric });
  const v = (n) => ins.data?.find((x) => x.name === n)?.values?.[0]?.value ?? null;
  const watch = v('ig_reels_avg_watch_time');
  return { views: v('views'), reach: v('reach'), saves: v('saved'), shares: v('shares'), interactions: v('total_interactions'),
    reposts: v('reposts'), skip: v('reels_skip_rate'),
    watch: watch == null ? null : Math.round(watch / 100) / 10 };  // seconds, 1 decimal
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
      let st = { views: null, reach: null, saves: null, shares: null, interactions: null, watch: null, reposts: null, skip: null };
      try { st = await insights(m.id, (m.media_product_type || m.media_type) === 'REELS'); } catch (e) { insightsError ??= e.message; }
      return {
        id: m.id, permalink: m.permalink, timestamp: m.timestamp, type: m.media_product_type || m.media_type,
        caption: m.caption ?? '', thumbnail: m.thumbnail_url || (m.media_type === 'IMAGE' ? m.media_url : null),
        likes: m.like_count ?? 0, comments: m.comments_count ?? 0, ...st, reel: null,
      };
    }));

    // Match queue reels to posts: by media id, by link, else by caption (posts made by hand reuse the reel's caption;
    // the time a reel was marked "posted" is not reliable, a post can be scheduled for later in the Instagram app).
    const items = (queue.data?.items ?? []).filter((i) => i.status === 'posted')
      .sort((x, y) => String(x.posted).localeCompare(String(y.posted)));
    const byId = new Map(posts.map((p) => [p.id, p]));
    const byCode = new Map(posts.map((p) => [shortcode(p.permalink), p]));
    const take = (it, p) => { if (p && !p.reel) { p.reel = it.id; return true; } return false; };
    const left = [];
    for (const it of items) {
      if (!(take(it, byId.get(it.ig_media_id)) || take(it, byCode.get(shortcode(it.permalink))))) left.push(it);
    }
    const oldestFirst = posts.slice().sort((x, y) => x.timestamp.localeCompare(y.timestamp));
    for (const it of left) {  // same caption: the oldest free post (reels with the same text are posted in order)
      const k = key(it.caption);
      if (k.length >= 20) take(it, oldestFirst.find((p) => !p.reel && key(p.caption) === k));
    }

    const media = {};
    for (const p of posts) if (p.reel) media[p.reel] = p;
    const sum = (k) => (posts.some((p) => p[k] != null) ? posts.reduce((n, p) => n + (p[k] ?? 0), 0) : null);
    const totals = {
      posts: posts.length, likes: sum('likes'), comments: sum('comments'), views: sum('views'),
      reach: sum('reach'), saves: sum('saves'), shares: sum('shares'), reposts: sum('reposts'),
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
