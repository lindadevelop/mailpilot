import { useCallback, useEffect, useState } from 'react';
import { api } from '../api';
import type { SubjectsReport } from '../types';

interface Props {
  onAbrir: (id: number) => void;
}

function formatarData(valor: string | null): string {
  if (!valor) return '—';
  const data = new Date(valor);
  return Number.isNaN(data.getTime()) ? '—' : data.toLocaleString('pt-PT');
}

/**
 * Resumo dos assuntos: junta os fios que são o mesmo tema ("Proposta" e
 * "RE: Proposta" contam juntos) e mostra quem escreve, quantas conversas há,
 * o que está por ler e o estado mais exigente do tema.
 */
export function ResumoAssuntos({ onAbrir }: Props) {
  const [dados, setDados] = useState<SubjectsReport | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [aCarregar, setACarregar] = useState(false);
  const [aberto, setAberto] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    setACarregar(true);
    setErro(null);
    try {
      setDados(await api.assuntos());
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Falha ao carregar o resumo dos assuntos.');
    } finally {
      setACarregar(false);
    }
  }, []);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  return (
    <section>
      <div className="filtros">
        <strong>Resumo dos assuntos</strong>
        <span className="rodape">
          {aCarregar
            ? 'A carregar…'
            : dados
              ? `${dados.total_temas} tema(s) em ${dados.total_conversas} conversa(s)`
              : '—'}
        </span>
        <span className="espaco" />
        <button onClick={() => void carregar()} disabled={aCarregar}>
          Atualizar
        </button>
      </div>

      {erro && <div className="erro">{erro}</div>}

      {dados && dados.items.length === 0 && !aCarregar && (
        <p className="vazio">Sem assuntos. Importe mensagens para começar a ver os temas agrupados.</p>
      )}

      {dados && dados.items.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Assunto</th>
              <th>Quem escreve</th>
              <th>Conversas</th>
              <th>Mensagens</th>
              <th>Por ler</th>
              <th>Estado</th>
              <th>Última</th>
            </tr>
          </thead>
          <tbody>
            {dados.items.map((t) => (
              <tr key={t.assunto}>
                <td>
                  <button className="ligacao" onClick={() => setAberto(aberto === t.assunto ? null : t.assunto)}>
                    {t.assunto}
                  </button>
                  {t.variantes.length > 0 && (
                    <div className="rodape" style={{ fontSize: 11 }}>
                      inclui: {t.variantes.join(' · ')}
                    </div>
                  )}
                  {aberto === t.assunto && (
                    <ul className="rodape" style={{ paddingLeft: 16, margin: '4px 0 0' }}>
                      {t.conversation_ids.map((id) => (
                        <li key={id}>
                          <button className="ligacao" onClick={() => onAbrir(id)}>
                            abrir conversa {id}
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </td>
                <td>
                  {t.remetentes.length === 0
                    ? '—'
                    : t.remetentes.map((r) => (
                        <div key={r} style={{ fontSize: 12 }}>
                          {r}
                        </div>
                      ))}
                </td>
                <td>{t.conversas}</td>
                <td>{t.mensagens}</td>
                <td>{t.por_ler > 0 ? <strong>{t.por_ler}</strong> : 0}</td>
                <td>
                  <span className={`etiqueta${t.estado === 'Indeterminado' ? ' alerta' : ''}`}>{t.estado}</span>
                </td>
                <td>{formatarData(t.ultima)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <p className="rodape">
        Os temas juntam «Re:», «Fwd:» e «Enc:» do mesmo assunto. O estado apresentado é o mais exigente das
        conversas que compõem o tema.
      </p>
    </section>
  );
}
