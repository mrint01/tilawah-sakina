import { REPO, fail, gh, guard, readBody, send, updateJson } from './_lib.js';

const now = () => new Date().toISOString().replace(/\.\d+Z$/, '+00:00');

function setStatus(id, status, note) {
  return updateJson('state/queue.json', (q) => {
    const it = (q.items ?? []).find((x) => x.id === id);
    if (!it) throw Object.assign(new Error('That reel is no longer in the queue.'), { status: 404 });
    if (it.status === 'posted') throw Object.assign(new Error('Already posted.'), { status: 409 });
    it.status = status;
    it.review = note || (status === 'approved' ? 'approved in panel' : status === 'pending' ? null : it.review);
    it.reviewed = now();
    return q;
  }, `${status === 'approved' ? 'Approve' : status === 'rejected' ? 'Reject' : 'Back to review'} ${id}`, { items: [] });
}

/** Reciters picked in Settings: { name: everyayah.com folder }, 1-20 of them. */
function cleanReciters(r) {
  const out = {};
  for (const [name, folder] of Object.entries(r ?? {}).slice(0, 20)) {
    const n = String(name).trim().slice(0, 60);
    if (n && typeof folder === 'string' && /^[A-Za-z0-9_.-]+(\/[A-Za-z0-9_.-]+)?$/.test(folder)) out[n] = folder;
  }
  if (!Object.keys(out).length) throw Object.assign(new Error('Keep at least one reciter.'), { status: 400 });
  return out;
}

const dispatch = (workflow, inputs) =>
  gh(`/repos/${REPO}/actions/workflows/${workflow}/dispatches`, { method: 'POST', body: { ref: 'main', inputs } });

export default async function handler(req, res) {
  if (!guard(req, res)) return;
  if (req.method !== 'POST') return send(res, 405, { error: 'method' });
  try {
    const b = await readBody(req);
    switch (b.type) {
      case 'approve':
        await setStatus(b.id, 'approved', b.note);
        break;
      case 'reject':
        if (!b.note?.trim()) return send(res, 400, { error: 'Say why it is rejected.' });
        await setStatus(b.id, 'rejected', b.note.trim());
        break;
      case 'schedule': {
        // "Change time": post this approved reel at a chosen time instead of its slot (at = null: back to the slots).
        // From the Not posted page it also lets the missed slot go.
        const at = b.at ? new Date(b.at) : null;
        if (at && (Number.isNaN(+at) || +at < Date.now() - 5 * 60_000 || +at > Date.now() + 60 * 86400_000))
          return send(res, 400, { error: 'Pick a time from now up to 60 days ahead.' });
        await updateJson('state/queue.json', (q) => {
          const it = (q.items ?? []).find((x) => x.id === b.id);
          if (!it || it.status !== 'approved') throw Object.assign(new Error('That reel is no longer approved.'), { status: 404 });
          if (at) it.post_at = at.toISOString().replace('.000Z', '+00:00'); else delete it.post_at;
          delete it.post_at_missed;
          const e = b.slot && q.slots?.[b.slot];
          if (e && (e.status === 'missed' || e.status === 'failed')) Object.assign(e, { status: 'resolved', resolved: new Date().toISOString() });
          return q;
        }, at ? `Panel: post ${b.id} at ${at.toISOString()}` : `Panel: ${b.id} back to the normal schedule`);
        break;
      }
      case 'slot_resolve':
        // "Keep in schedule" on the Not posted page: the slot is let go, its reel stays approved for its next slot
        if (!/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/.test(b.slot || '')) return send(res, 400, { error: 'Unknown slot.' });
        await updateJson('state/queue.json', (q) => {
          const e = q.slots?.[b.slot];
          if (!e) throw Object.assign(new Error('That slot is not in the log.'), { status: 404 });
          if (e.status === 'missed' || e.status === 'failed') Object.assign(e, { status: 'resolved', resolved: new Date().toISOString() });
          return q;
        }, `Panel: slot ${b.slot} kept in the schedule`);
        break;
      case 'requeue':
        await setStatus(b.id, 'pending', null);
        break;
      case 'mark_posted': {
        const link = String(b.permalink || '').trim();
        if (link && !/^https:\/\/(www\.)?instagram\.com\//.test(link)) return send(res, 400, { error: 'That is not an Instagram link.' });
        await updateJson('state/queue.json', (q) => {
          const it = (q.items ?? []).find((x) => x.id === b.id);
          if (!it) throw Object.assign(new Error('That reel is no longer in the queue.'), { status: 404 });
          if (it.status !== 'approved') throw Object.assign(new Error('Only approved reels can be marked as posted.'), { status: 409 });
          it.status = 'posted';
          it.posted = now();
          it.manual = true;
          if (link) it.permalink = link;
          return q;
        }, `Posted by hand ${b.id}`, { items: [] });
        break;
      }
      case 'unmark_posted':
        // Undo a mistaken "I posted it": only for reels marked by hand (auto-posted ones are really on Instagram).
        await updateJson('state/queue.json', (q) => {
          const it = (q.items ?? []).find((x) => x.id === b.id);
          if (!it) throw Object.assign(new Error('That reel is no longer in the queue.'), { status: 404 });
          if (it.status !== 'posted' || !it.manual) throw Object.assign(new Error('Only reels marked as posted by hand can be undone.'), { status: 409 });
          it.status = 'approved';
          delete it.posted; delete it.manual; delete it.permalink;
          return q;
        }, `Not posted after all ${b.id}`, { items: [] });
        break;
      case 'toggle':
        await updateJson('state/config.json', (c) => ({ ...c, enabled: Boolean(b.enabled) }),
          `Automation ${b.enabled ? 'ON' : 'OFF'}`);
        break;
      case 'settings': {
        const s = b.settings ?? {};
        if (s.config) {
          await updateJson('state/config.json', (c) => ({
            ...c,
            ...(Number.isFinite(s.config.buffer_days) ? { buffer_days: Math.max(1, Math.min(14, Math.round(s.config.buffer_days))) } : {}),
            ...(s.config.reciters ? { reciters: cleanReciters(s.config.reciters) } : {}),
          }), 'Update automation settings');
        }
        if (s.panel) {
          await updateJson('state/panel.json', (p) => ({ ...p, name: String(s.panel.name ?? '').slice(0, 60) }), 'Update panel profile');
        }
        break;
      }
      case 'post_now':
        // "Publish now" on one reel (its id), or the next reel of a kind / of the nearest slot
        if (b.id && !/^\d{8}-\d{6}-(ayah|tasbih|dua|asma|quiz|story)$/.test(b.id)) return send(res, 400, { error: 'Unknown reel.' });
        await dispatch('post.yml', { dry_run: 'false', id: b.id || '', slot: b.id && /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/.test(b.slot || '') ? b.slot : '', kind: ['ayah', 'dua', 'asma', 'tasbih', 'quiz'].includes(b.kind) ? b.kind : 'auto' });
        break;
      case 'generate': {
        // From the "Make reels" popup: a list of jobs (surah / start ayah / reciter, a tasbih kind, a dua kind,
        // a name of Allah, or a quiz level).
        const SETS = ['subhanallah', 'alhamdulillah', 'allahuakbar', 'wabihamdihi', 'astaghfirullah', 'tahlil', 'salawat'];
        const DUAS = ['morning', 'after_salah', 'need', 'friday', 'arafah'];
        const LEVELS = ['easy', 'medium', 'hard'];
        const int = (v, lo, hi) => { const n = Math.trunc(Number(v)); return n >= lo && n <= hi ? n : null; };
        if (Array.isArray(b.jobs)) {
          const jobs = b.jobs.slice(0, 10).map((j) => {
            if (j?.kind === 'tasbih') return { kind: 'tasbih', ...(SETS.includes(j.set) ? { set: j.set } : {}) };
            if (j?.kind === 'dua') return { kind: 'dua', ...(DUAS.includes(j.category) ? { category: j.category } : {}) };
            if (j?.kind === 'asma') {
              const number = int(j.number, 1, 99);
              return { kind: 'asma', ...(number ? { number } : {}), ...(typeof j.reciter === 'string' && j.reciter.length <= 60 ? { reciter: j.reciter } : {}) };
            }
            if (j?.kind === 'quiz') return { kind: 'quiz', ...(LEVELS.includes(j.level) ? { level: j.level } : {}) };
            const surah = int(j?.surah, 1, 114);
            const ayah = surah ? int(j?.ayah, 1, 286) : null;
            return {
              kind: 'ayah',
              ...(surah && ayah ? { start: [surah, ayah] } : surah ? { surah } : {}),
              // a reciter from Settings → Reciters (pipeline.py falls back to a random one if unknown)
              ...(typeof j?.reciter === 'string' && j.reciter.length <= 60 ? { reciter: j.reciter } : {}),
            };
          });
          if (!jobs.length) throw Object.assign(new Error('Pick at least one reel to make.'), { status: 400 });
          await dispatch('generate.yml', { ayah: '0', tasbih: '0', spec: JSON.stringify(jobs) });  // spec overrides the counts
        } else {
          await dispatch('generate.yml', {
            ayah: String(Math.max(0, Math.min(10, Number(b.ayah ?? 1)))),
            tasbih: String(Math.max(0, Math.min(10, Number(b.tasbih ?? 1)))),
          });
        }
        break;
      }
      default:
        return send(res, 400, { error: 'unknown action' });
    }
    send(res, 200, { ok: true });
  } catch (e) {
    fail(res, e);
  }
}
