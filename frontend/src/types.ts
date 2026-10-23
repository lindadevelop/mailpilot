export type PendencyState =
  | 'Preciso responder'
  | 'Aguardo resposta de terceiros'
  | 'Preciso executar tarefa'
  | 'Acompanhar'
  | 'Em análise'
  | 'Resolvido'
  | 'Informativo'
  | 'Indeterminado';

export interface Dashboard {
  total_messages: number;
  unread_messages: number;
  conversations_by_state: Record<string, number>;
  preciso_responder: number;
  aguardo_terceiros: number;
  atrasados: number;
}

export interface Conversation {
  /** Quem escreveu (a contraparte, isto é, a última mensagem recebida). */
  sender?: string | null;
  sender_domain?: string | null;
  /** Autor da última mensagem, seja recebida ou enviada. */
  last_sender?: string | null;
  last_direction?: string | null;
  unread?: number;
  id: number;
  subject: string | null;
  state: PendencyState | string;
  message_count: number;
  last_message_at: string | null;
}

export interface ConversationPage {
  total: number;
  items: Conversation[];
}

export interface SyncStatus {
  account_email: string | null;
  source: string | null;
  cursor: string | null;
  last_run_id: number | null;
  message_count: number;
  conversation_count: number;
}

export interface AnalysisEvidence {
  message_id: number;
  quote: string | null;
}

export interface Analysis {
  id: number;
  state: string;
  reason: string | null;
  confidence: number | null;
  deadline_text: string | null;
  commitments: string | null;
  model: string | null;
  created_at: string | null;
  evidence: AnalysisEvidence[];
}

export interface Draft {
  id: number;
  mode: string;
  subject: string | null;
  body: string;
  status: string;
  created_at: string | null;
}

export const DRAFT_MODES = ['objetivo', 'diplomatico', 'tecnico', 'firme_cordial'] as const;
export type DraftMode = (typeof DRAFT_MODES)[number];

export interface SubjectSummary {
  assunto: string;
  variantes: string[];
  conversas: number;
  mensagens: number;
  por_ler: number;
  estado: string;
  estados: Record<string, number>;
  remetentes: string[];
  dominios: string[];
  ultima: string | null;
  conversation_ids: number[];
}

export interface SubjectsReport {
  total_temas: number;
  total_conversas: number;
  items: SubjectSummary[];
}
