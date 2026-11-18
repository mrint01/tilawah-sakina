// Shared helpers for the panel's serverless functions (files starting with _ are not routes on Vercel).
import crypto from 'node:crypto';

export const REPO = process.env.GITHUB_REPO || 'mrint01/tilawah-sakina';
export const ASSETS = `https://github.com/${REPO}/releases/download/queue/`;
const COOKIE = 'ts_session';
const MAX_AGE = 30 * 24 * 3600;
const secret = () => process.env.SESSION_SECRET || process.env.PANEL_PASSWORD || '';

export function send(res, code, data, headers = {}) {
  res.statusCode = code;
  res.setHeader('content-type', 'application/json');
  res.setHeader('cache-control', 'no-store');
  for (const [k, v] of Object.entries(headers)) res.setHeader(k, v);
  res.end(JSON.stringify(data));
}

export async function readBody(req) {
  if (req.body && typeof req.body === 'object') return req.body;
  if (typeof req.body === 'string') return JSON.parse(req.body || '{}');
  const chunks = [];
  for await (const c of req) chunks.push(c);
  const raw = Buffer.concat(chunks).toString('utf8');
  return raw ? JSON.parse(raw) : {};
}

const sign = (v) => crypto.createHmac('sha256', secret()).update(v).digest('base64url');

export function sessionCookie() {
  const exp = String(Date.now() + MAX_AGE * 1000);
  return `${COOKIE}=${exp}.${sign(exp)}; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=${MAX_AGE}`;
}
export const clearCookie = () => `${COOKIE}=; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=0`;

export function isAuthed(req) {
  const raw = (req.headers.cookie || '').split(';').map((s) => s.trim()).find((s) => s.startsWith(`${COOKIE}=`));
  if (!raw || !secret()) return false;
  const [exp, mac] = raw.slice(COOKIE.length + 1).split('.');
  if (!exp || !mac || Number(exp) < Date.now()) return false;
  const a = Buffer.from(mac);
  const b = Buffer.from(sign(exp));
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

export function passwordMatches(given) {
  const want = process.env.PANEL_PASSWORD || '';
  const a = crypto.createHash('sha256').update(String(given || '')).digest();
  const b = crypto.createHash('sha256').update(want).digest();
  return want.length > 0 && crypto.timingSafeEqual(a, b);
}

/** Returns true when the request may continue; otherwise it has already answered. */
export function guard(req, res) {
  if (!process.env.PANEL_PASSWORD) {
    send(res, 500, { error: 'PANEL_PASSWORD is not set in the Vercel environment.' });
    return false;
  }
  if (!isAuthed(req)) {
    send(res, 401, { error: 'signed_out' });
    return false;
  }
  return true;
}

export async function gh(path, { method = 'GET', body } = {}) {
  if (!process.env.GITHUB_TOKEN) throw new Error('GITHUB_TOKEN is not set in the Vercel environment.');
  const r = await fetch(`https://api.github.com${path}`, {
    method,
    headers: {
      authorization: `Bearer ${process.env.GITHUB_TOKEN}`,
      accept: 'application/vnd.github+json',
      'x-github-api-version': '2022-11-28',
      'user-agent': 'reel-studio',
      ...(body ? { 'content-type': 'application/json' } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (r.status === 204) return null;
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    const err = new Error(`GitHub ${r.status}: ${data.message || 'request failed'}`);
    err.status = r.status;
    throw err;
  }
  return data;
}

/** Reads a JSON file from the repo (fresh, not the raw CDN). Missing file -> { data: null, sha: null }. */
export async function readJson(path) {
  try {
    const r = await gh(`/repos/${REPO}/contents/${path}?ref=main`);
    return { data: JSON.parse(Buffer.from(r.content, 'base64').toString('utf8')), sha: r.sha };
  } catch (e) {
    if (e.status === 404) return { data: null, sha: null };
    throw e;
  }
}

/** Read-modify-write a JSON file with a commit; retries when a workflow pushed in between. */
export async function updateJson(path, mutate, message, fallback = {}) {
  for (let attempt = 0; attempt < 4; attempt++) {
    const { data, sha } = await readJson(path);
    const next = mutate(structuredClone(data ?? fallback));
    try {
      await gh(`/repos/${REPO}/contents/${path}`, {
        method: 'PUT',
        body: {
          message: `${message}\n\nFrom Reel Studio`,
          content: Buffer.from(JSON.stringify(next, null, 2) + '\n', 'utf8').toString('base64'),
          branch: 'main',
          ...(sha ? { sha } : {}),
        },
      });
      return next;
    } catch (e) {
      if ((e.status === 409 || e.status === 422) && attempt < 3) continue;
      throw e;
    }
  }
  throw new Error('Could not save, please try again.');
}

export function fail(res, e) {
  send(res, e.status && e.status < 500 ? 502 : 500, { error: e.message || String(e) });
}
