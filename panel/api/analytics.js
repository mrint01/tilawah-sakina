import { fail, guard, readJson, send } from './_lib.js';

/** Account numbers per day (state/daily.json, filled by the Daily stats workflow) for the Analytics page. */
export default async function handler(req, res) {
  if (!guard(req, res)) return;
  try {
    const daily = await readJson('state/daily.json');
    send(res, 200, { days: daily.data?.days ?? {}, updated: daily.data?.updated ?? null });
  } catch (e) {
    fail(res, e);
  }
}
