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
      case 'requeue':
        await setStatus(b.id, 'pending', null);
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
            ...(Array.isArray(s.config.alternate) ? { alternate: s.config.alternate.filter((k) => ['ayah', 'tasbih'].includes(k)) } : {}),
            ...(Number.isFinite(s.config.buffer) ? { buffer: Math.max(2, Math.min(60, Math.round(s.config.buffer))) } : {}),
          }), 'Update automation settings');
        }
        if (s.panel) {
          await updateJson('state/panel.json', (p) => ({ ...p, name: String(s.panel.name ?? '').slice(0, 60) }), 'Update panel profile');
        }
        break;
      }
      case 'post_now':
        await dispatch('post.yml', { dry_run: 'false' });
        break;
      case 'generate':
        await dispatch('generate.yml', {
          ayah: String(Math.max(0, Math.min(10, Number(b.ayah ?? 1)))),
          tasbih: String(Math.max(0, Math.min(10, Number(b.tasbih ?? 1)))),
        });
        break;
      default:
        return send(res, 400, { error: 'unknown action' });
    }
    send(res, 200, { ok: true });
  } catch (e) {
    fail(res, e);
  }
}
