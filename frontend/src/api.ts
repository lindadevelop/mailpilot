import type { ConversationPage, Dashboard, SyncStatus } from './types';

/**
 * Cliente da API local. A chave é guardada no browser (localStorage) e enviada
 * em `X-API-Key`: não é escrita no código nem vai para o bundle.
 */
const CHAVE_STORAGE = 'mailpilot.apiKey';
const URL_BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? '';

export function getApiKey(): string {
  return window.localStorage.getItem(CHAVE_STORAGE) ?? '';
}

export function setApiKey(valor: string): void {
  window.localStorage.setItem(CHAVE_STORAGE, valor.trim());
}

export class ApiError extends Error {}

async function pedir<T>(caminho: string): Promise<T> {
  const resposta = await fetch(`${URL_BASE}${caminho}`, {
    headers: { 'X-API-Key': getApiKey() },
  });
  if (resposta.status === 401) {
    throw new ApiError('Chave de API inválida ou ausente. Confirme a chave em cima.');
  }
  if (!resposta.ok) {
    throw new ApiError(`A API respondeu ${resposta.status} em ${caminho}.`);
  }
  return (await resposta.json()) as T;
}

export const api = {
  dashboard: () => pedir<Dashboard>('/api/dashboard'),
  conversas: (filtros: { state?: string; search?: string } = {}) => {
    const params = new URLSearchParams();
    if (filtros.state) params.set('state', filtros.state);
    const query = params.toString();
    return pedir<ConversationPage>(`/api/conversations${query ? `?${query}` : ''}`);
  },
  estadoSincronizacao: (conta: string, origem = 'import') =>
    pedir<SyncStatus>(`/api/sync/status?account_email=${encodeURIComponent(conta)}&source=${origem}`),
  saude: () => pedir<{ status: string; app: string }>('/health'),
};
