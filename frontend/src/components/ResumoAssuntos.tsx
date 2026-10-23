import { useCallback, useEffect, useState } from 'react';
import { api } from '../api';
import type { SubjectSummary, SubjectsReport } from '../types';
import { Grelha, type Coluna } from './Grelha';

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

  const colunas: Coluna<SubjectSummary>[] = [
    {
      chave: 'assunto',
      titulo: 'Assunto',
      valor: (t) => t.assunto,
      render: (t) => (
        <>
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
        </>
      ),
    },
    {
      chave: 'remetentes',
      titulo: 'Quem escreve',
      valor: (t) => t.remetentes.join(', '),
      render: (t) =>
        t.remetentes.length === 0 ? (
          '—'
        ) : (
          <>
            {t.remetentes.map((r) => (
              <div key={r} style={{ fontSize: 12 }}>
                {r}
              </div>
            ))}
          </>
        ),
    },
    { chave: 'conversas', titulo: 'Conversas', valor: (t) => t.conversas },
    { chave: 'mensagens', titulo: 'Mensagens', valor: (t) => t.mensagens },
    {
      chave: 'por_ler',
      titulo: 'Por ler',
      valor: (t) => t.por_ler,
      render: (t) => (t.por_ler > 0 ? <strong>{t.por_ler}</strong> : 0),
    },
    {
      chave: 'estado',
      titulo: 'Estado',
      valor: (t) => t.estado,
      render: (t) => (
        <span className={`etiqueta${t.estado === 'Indeterminado' ? ' alerta' : ''}`}>{t.estado}</span>
      ),
    },
    {
      chave: 'ultima',
      titulo: 'Última',
      valor: (t) => t.ultima ?? '',
      render: (t) => formatarData(t.ultima),
    },
  ];

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

      <Grelha
        linhas={dados?.items ?? []}
        colunas={colunas}
        chaveLinha={(t) => t.assunto}
        agrupaveis={['estado', 'remetentes']}
        textoVazio="Sem assuntos. Importe mensagens para começar a ver os temas agrupados."
      />

      <p className="rodape">
        Os temas juntam «Re:», «Fwd:» e «Enc:» do mesmo assunto. O estado apresentado é o mais exigente das
        conversas que compõem o tema.
      </p>
    </section>
  );
}
