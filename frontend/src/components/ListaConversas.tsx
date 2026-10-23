import type { Conversation } from '../types';
import { Grelha, type Coluna } from './Grelha';

interface Props {
  conversas: Conversation[];
  total: number;
  aCarregar: boolean;
  filtroEstado: string;
  onFiltroEstado: (valor: string) => void;
  onAbrir: (id: number) => void;
}

const ESTADOS = [
  'Preciso responder',
  'Aguardo resposta de terceiros',
  'Preciso executar tarefa',
  'Acompanhar',
  'Em análise',
  'Resolvido',
  'Informativo',
  'Indeterminado',
];

function formatarData(valor: string | null): string {
  if (!valor) return '—';
  const data = new Date(valor);
  return Number.isNaN(data.getTime()) ? '—' : data.toLocaleString('pt-PT');
}

export function ListaConversas({ conversas, total, aCarregar, filtroEstado, onFiltroEstado, onAbrir }: Props) {
  const colunas: Coluna<Conversation>[] = [
    {
      chave: 'assunto',
      titulo: 'Assunto',
      valor: (c) => c.subject ?? '(sem assunto)',
      render: (c) => (
        <>
          <button className="ligacao" onClick={() => onAbrir(c.id)}>
            {c.subject ?? '(sem assunto)'}
          </button>
          {c.last_sender && c.last_sender !== c.sender && (
            <div className="rodape" style={{ fontSize: 11 }}>
              última mensagem: {c.last_sender}
              {c.last_direction === 'out' ? ' (enviada por nós)' : ''}
            </div>
          )}
        </>
      ),
    },
    {
      chave: 'remetente',
      titulo: 'Quem enviou',
      valor: (c) => c.sender ?? '',
      render: (c) => <span style={{ fontSize: 12 }}>{c.sender ?? '—'}</span>,
    },
    {
      chave: 'estado',
      titulo: 'Estado',
      valor: (c) => c.state,
      render: (c) => (
        <span className={`etiqueta${c.state === 'Indeterminado' ? ' alerta' : ''}`}>{c.state}</span>
      ),
    },
    {
      chave: 'mensagens',
      titulo: 'Mensagens',
      valor: (c) => c.message_count,
      render: (c) => (
        <>
          {c.message_count}
          {c.unread ? <span className="rodape"> · {c.unread} por ler</span> : null}
        </>
      ),
    },
    {
      chave: 'por_ler',
      titulo: 'Por ler',
      valor: (c) => c.unread ?? 0,
      render: (c) => (c.unread ? <strong>{c.unread}</strong> : 0),
    },
    {
      chave: 'ultima',
      titulo: 'Última',
      valor: (c) => c.last_message_at ?? '',
      render: (c) => formatarData(c.last_message_at),
    },
  ];

  return (
    <>
      <div className="filtros">
        <label htmlFor="filtro-estado">Estado (filtra no servidor)</label>
        <select id="filtro-estado" value={filtroEstado} onChange={(e) => onFiltroEstado(e.target.value)}>
          <option value="">Todos</option>
          {ESTADOS.map((estado) => (
            <option key={estado} value={estado}>
              {estado}
            </option>
          ))}
        </select>
        <span className="rodape">
          {aCarregar ? 'A carregar…' : `${conversas.length} de ${total} conversa(s)`}
        </span>
      </div>

      <Grelha
        linhas={conversas}
        colunas={colunas}
        chaveLinha={(c) => c.id}
        agrupaveis={['estado', 'remetente']}
        textoVazio="Sem conversas. Importe mensagens pela API (POST /api/emails/batch) para começar."
      />
    </>
  );
}
