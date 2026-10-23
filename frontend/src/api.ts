import type { Analysis, ConversationPage, Dashboard, Draft, SubjectsReport, SyncStatus } from './types';

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
  // Sem chave guardada (modo proxy) não se envia o cabeçalho: é o proxy do
  // Vite que autentica. Enviar um cabeçalho vazio estragaria o pedido.
  const cabecalhos: Record<string, string> = {};
  const chave = getApiKey();
  if (chave) cabecalhos['X-API-Key'] = chave;
  const resposta = await fetch(`${URL_BASE}${caminho}`, { headers: cabecalhos });
  if (resposta.status === 401) {
    throw new ApiError('Chave de API inválida ou ausente. Confirme a chave em cima.');
  }
  if (resposta.status === 404) {
    throw new ApiError(
      'Este endpoint ainda não está disponível — a API precisa de ser reiniciada com o código atual.',
    );
  }
  if (!resposta.ok) {
    throw new ApiError(`A API respondeu ${resposta.status} em ${caminho}.`);
  }
  return (await resposta.json()) as T;
}

async function enviar<T>(caminho: string, corpo: unknown): Promise<T> {
  const resposta = await fetch(`${URL_BASE}${caminho}`, {
    method: 'POST',
    headers: { 'X-API-Key': getApiKey(), 'Content-Type': 'application/json' },
    body: JSON.stringify(corpo),
  });
  if (resposta.status === 401) {
    throw new ApiError('Chave de API inválida ou ausente.');
  }
  if (resposta.status === 503) {
    throw new ApiError('O Ollama não está acessível — a classificação/gereção precisa dele a correr.');
  }
  if (!resposta.ok) {
    let detalhe = `A API respondeu ${resposta.status}.`;
    try {
      const corpoErro = (await resposta.json()) as { detail?: string };
      if (corpoErro.detail) detalhe = corpoErro.detail;
    } catch {
      /* resposta sem JSON */
    }
    throw new ApiError(detalhe);
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
  analise: (conversationId: number) =>
    pedir<{ conversation_id: number; analysis: Analysis | null }>(
      `/api/conversations/${conversationId}/analysis`,
    ),
  rascunhos: (conversationId: number) =>
    pedir<{ total: number; items: Draft[] }>(`/api/conversations/${conversationId}/drafts`),
  gerarRascunho: (conversationId: number, mode: string, instructions?: string) =>
    enviar<{
      ok: boolean;
      draft_id: number;
      mode: string;
      subject: string | null;
      body: string;
      facts_used: string[];
      open_questions: string[];
      aviso: string;
    }>(`/api/conversations/${conversationId}/draft`, { mode, instructions: instructions ?? null }),
  reverRascunho: (draftId: number, reviewedBy: string, discard = false) =>
    enviar<{ ok: boolean; status: string }>(`/api/drafts/${draftId}/review`, {
      reviewed_by: reviewedBy,
      discard,
    }),
  alteracoes: (horas = 24) => pedir<Record<string, unknown>>(`/api/reports/changes?horas=${horas}`),
  assuntos: (limite = 50) => pedir<SubjectsReport>(`/api/reports/subjects?limite=${limite}`),
};
