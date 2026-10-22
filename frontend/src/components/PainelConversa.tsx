import type { Conversation } from '../types';

interface Props {
  conversa: Conversation;
  onFechar: () => void;
}

/**
 * Detalhe da conversa. Nesta fase mostra o que existe (assunto, estado, número de
 * mensagens); o resumo por IA, as evidências e as ações são da Fase 2.
 */
export function PainelConversa({ conversa, onFechar }: Props) {
  return (
    <div className="cartao" style={{ marginBottom: 16 }}>
      <div className="filtros">
        <strong>{conversa.subject ?? '(sem assunto)'}</strong>
        <span className="etiqueta">{conversa.state}</span>
        <span className="espaco" style={{ flex: 1 }} />
        <button onClick={onFechar}>Fechar</button>
      </div>
      <p className="rodape">
        {conversa.message_count} mensagem(ns) · última:{' '}
        {conversa.last_message_at ? new Date(conversa.last_message_at).toLocaleString('pt-PT') : '—'}
      </p>
      <p className="rodape">
        Resumo por IA, evidências e ações (resolver, adiar, acompanhar) chegam na Fase 2 — nada é
        inventado nesta fase.
      </p>
    </div>
  );
}
