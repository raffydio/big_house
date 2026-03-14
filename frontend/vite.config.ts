import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Tutte le route backend — mancavano /billing e /storage
      '/auth':     { target: 'http://localhost:8000', changeOrigin: true },
      '/users':    { target: 'http://localhost:8000', changeOrigin: true },
      '/features': { target: 'http://localhost:8000', changeOrigin: true },
      '/billing':  { target: 'http://localhost:8000', changeOrigin: true },  // ← mancava
      '/storage':  { target: 'http://localhost:8000', changeOrigin: true },  // ← mancava
      '/health':   { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
});