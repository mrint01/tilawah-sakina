import { ASSETS, REPO, fail, gh, guard, readJson, send } from './_lib.js';

/** Everything the panel shows: queue, settings, latest workflow runs. */
export default async function handler(req, res) {
  if (!guard(req, res)) return;
  try {
    const [queue, config, panel, runs, progress, weekly] = await Promise.all([
      readJson('state/queue.json'),
      readJson('state/config.json'),
      readJson('state/panel.json'),
      gh(`/repos/${REPO}/actions/runs?per_page=12`),
      // live render progress, written by pipeline.py into the release while it works
      fetch(`${ASSETS}progress.json?t=${Date.now()}`, { cache: 'no-store' }).then((r) => (r.ok ? r.json() : null)).catch(() => null),
      readJson('state/weekly.json'),
    ]);
    send(res, 200, {
      repo: REPO,
      assets: ASSETS,
      items: queue.data?.items ?? [],
      config: { enabled: true, alternate: ['ayah', 'tasbih'], buffer: 14, reciters: { 'Mishary Alafasy': 'Alafasy_128kbps', 'Maher Al-Muaiqly': 'quranicaudio/maher_256', 'Yasser Al-Dosari': 'Yasser_Ad-Dussary_128kbps' }, ...(config.data ?? {}) },
      panel: { name: '', ...(panel.data ?? {}) },
      instagram: Boolean(process.env.IG_ACCESS_TOKEN),
      progress,
      // reels posted again every week (Friday Al-Kahf); their files are in the 'weekly' release
      weekly: { assets: `https://github.com/${REPO}/releases/download/weekly/`, items: weekly.data?.items ?? [], posted: weekly.data?.posted ?? [] },
      runs: (runs.workflow_runs ?? []).map((r) => ({
        id: r.id, name: r.name, event: r.event, status: r.status, conclusion: r.conclusion,
        created: r.created_at, url: r.html_url, title: r.display_title,
      })),
    });
  } catch (e) {
    fail(res, e);
  }
}
