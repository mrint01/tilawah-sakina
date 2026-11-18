import { clearCookie, passwordMatches, readBody, send, sessionCookie } from './_lib.js';

export default async function handler(req, res) {
  if (req.method === 'DELETE') return send(res, 200, { ok: true }, { 'set-cookie': clearCookie() });
  if (req.method !== 'POST') return send(res, 405, { error: 'method' });
  if (!process.env.PANEL_PASSWORD) return send(res, 500, { error: 'PANEL_PASSWORD is not set in the Vercel environment.' });
  const { password } = await readBody(req);
  if (!passwordMatches(password)) {
    await new Promise((r) => setTimeout(r, 800)); // slows down guessing
    return send(res, 401, { error: 'Wrong password.' });
  }
  send(res, 200, { ok: true }, { 'set-cookie': sessionCookie() });
}
