import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// In dev, /api goes to dev-api.mjs (the same handlers Vercel runs in production).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { '/api': 'http://localhost:3001' } },
});
