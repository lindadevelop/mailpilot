import type { Conversation } from '../types';

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
  return (
    <section>
      <div className="filtros">
        <label htmlFor="filtro-estado">Estado</label>
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

      {conversas.length === 0 && !aCarregar ? (
        <p className="vazio">
          Sem conversas. Importe mensagens pela API (<code>POST /api/emails/batch</code>) para começar.
        </p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Assunto</th>
              <th>Quem enviou</th>
              <th>Estado</th>
              <th>Mensagens</th>
              <th>Última</th>
            </tr>
          </thead>
          <tbody>
            {conversas.map((c) => (
              <tr key={c.id}>
                <td>
                  <button className="ligacao" onClick={() => onAbrir(c.id)}>
                    {c.subject ?? '(sem assunto)'}
                  </button>
                </td>
                <td>
                  <div style={{ fontSize: 12 }}>{c.sender ?? '—'}</div>
                  {c.last_sender && c.last_sender !== c.sender && (
                    <div className="rodape" style={{ fontSize: 11 }}>
                      última: {c.last_sender}
                      {c.last_direction === 'out' ? ' (enviada por nós)' : ''}
                    </div>
                  )}
                </td>
                <td>
                  <span className={`etiqueta${c.state === 'Indeterminado' ? ' alerta' : ''}`}>{c.state}</span>
                </td>
                <td>
                  {c.message_count}
                  {c.unread ? <span className="rodape"> · {c.unread} por ler</span> : null}
                </td>
                <td>{formatarData(c.last_message_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
