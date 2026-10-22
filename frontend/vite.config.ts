import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

/**
 * O frontend fala com a API local em 127.0.0.1:8100 através de proxy, para não
 * ter de configurar CORS nem expor a API fora de localhost.
 */
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8100', changeOrigin: true },
      '/health': { target: 'http://127.0.0.1:8100', changeOrigin: true },
    },
  },
  // O `vite preview` (build de produção) não herda o proxy do servidor de
  // desenvolvimento — sem isto, a pré-visualização não falava com a API.
  preview: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8100', changeOrigin: true },
      '/health': { target: 'http://127.0.0.1:8100', changeOrigin: true },
    },
  },
});
