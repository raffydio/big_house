import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Proxy API calls in dev verso il backend FastAPI
      '/auth':     { target: 'http://localhost:8000', changeOrigin: true },
      '/users':    { target: 'http://localhost:8000', changeOrigin: true },
      '/features': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
});
