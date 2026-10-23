import path from 'node:path';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

/**
 * Notas de configuração:
 *  - `allowedHosts: true` porque o domínio do túnel (trycloudflare.com) é
 *    dinâmico: sem isto o Vite recusa o Host com 403.
 *  - A chave da API é injetada **no proxy** (a partir do `.env` do projecto,
 *    variável `API_KEY`), para que a interface não volte a pedi-la quando o
 *    domínio do túnel muda — o browser guarda chaves por domínio.
 *    O browser nunca recebe a chave; ela viaja só entre o proxy e a API local.
 */
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, path.resolve(__dirname, '..'), '');
  const chave = env.API_KEY?.trim();
  if (!chave) {
    // Não é fatal: a interface ainda aceita a chave escrita à mão.
    console.warn('[vite] API_KEY ausente no .env — o proxy não autentica os pedidos.');
  }
  const cabecalhos = chave ? { 'X-API-Key': chave } : undefined;

  return {
    plugins: [react()],
    server: {
      port: 5173,
      allowedHosts: true,
      proxy: {
        '/api': { target: 'http://127.0.0.1:8100', changeOrigin: true, headers: cabecalhos },
        '/health': { target: 'http://127.0.0.1:8100', changeOrigin: true, headers: cabecalhos },
      },
    },
    // O `vite preview` (build de produção) não herda o proxy do servidor de
    // desenvolvimento — sem isto, a pré-visualização não fala com a API.
    preview: {
      port: 5175,
      allowedHosts: true,
      proxy: {
        '/api': { target: 'http://127.0.0.1:8100', changeOrigin: true, headers: cabecalhos },
        '/health': { target: 'http://127.0.0.1:8100', changeOrigin: true, headers: cabecalhos },
      },
    },
  };
});
