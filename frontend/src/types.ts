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
