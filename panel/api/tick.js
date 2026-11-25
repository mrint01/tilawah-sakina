import { REPO, gh, send } from './_lib.js';

/**
 * Vercel cron (vercel.json): a second trigger next to GitHub's own schedule, which sometimes skips runs for hours.
 * job=post starts post.yml in "due" mode (posts the current slot only if it is not posted yet, so a double start is
 * harmless); job=generate starts the daily reel making (it makes nothing when every type is already stocked).
 */
export default async function handler(req, res) {
  const secret = process.env.CRON_SECRET;
  const auth = req.headers.authorization || '';
  const fromCron = secret ? auth === `Bearer ${secret}` : String(req.headers['user-agent'] || '').startsWith('vercel-cron');
  if (!fromCron) return send(res, 401, { error: 'cron only' });
  const job = new URL(req.url, 'http://x').searchParams.get('job');
  try {
    if (job === 'post') {
      await gh(`/repos/${REPO}/actions/workflows/post.yml/dispatches`, { method: 'POST', body: { ref: 'main', inputs: { kind: 'due', id: '', dry_run: 'false' } } });
    } else if (job === 'generate') {
      await gh(`/repos/${REPO}/actions/workflows/generate.yml/dispatches`, { method: 'POST', body: { ref: 'main', inputs: { auto: 'true' } } });
    } else {
      return send(res, 400, { error: 'unknown job' });
    }
    send(res, 200, { ok: true, job });
  } catch (e) {
    send(res, 500, { error: String(e.message || e) });
  }
}
