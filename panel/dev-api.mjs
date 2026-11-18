// Local stand-in for Vercel: serves api/*.js on :3001 (Vite proxies /api here).
//   GITHUB_TOKEN=$(gh auth token) PANEL_PASSWORD=test npm run dev:api
import http from 'node:http';
import { existsSync } from 'node:fs';

const port = 3001;
http.createServer(async (req, res) => {
  const name = new URL(req.url, 'http://x').pathname.replace(/^\/api\//, '').replace(/[^a-z_-]/gi, '');
  const file = new URL(`./api/${name}.js`, import.meta.url);
  if (!name || name.startsWith('_') || !existsSync(file)) {
    res.statusCode = 404;
    return res.end('{"error":"not found"}');
  }
  try {
    const mod = await import(file.href);
    await mod.default(req, res);
  } catch (e) {
    console.error(e);
    res.statusCode = 500;
    res.end(JSON.stringify({ error: e.message }));
  }
}).listen(port, () => console.log(`api on http://localhost:${port}`));
