import { Fragment, useMemo, useState, type ReactNode } from 'react';

export interface Coluna<T> {
  chave: string;
  titulo: string;
  /** Valor usado para ordenar, agrupar e pesquisar. */
  valor: (linha: T) => string | number | null;
  /** Como desenhar a célula (por omissão, o valor em texto). */
  render?: (linha: T) => ReactNode;
}

interface Props<T> {
  linhas: T[];
  colunas: Coluna<T>[];
  chaveLinha: (linha: T) => string | number;
  /** Colunas (por chave) que podem servir de agrupamento. */
  agrupaveis?: string[];
  porPaginaInicial?: number;
  textoVazio?: string;
}

type Direcao = 'asc' | 'desc';

function comparar(a: string | number | null, b: string | number | null): number {
  if (a === null || a === undefined || a === '') return 1;
  if (b === null || b === undefined || b === '') return -1;
  if (typeof a === 'number' && typeof b === 'number') return a - b;
  return String(a).localeCompare(String(b), 'pt-PT', { numeric: true, sensitivity: 'base' });
}

/**
 * Grelha com ordenação por coluna, agrupamento, pesquisa e paginação.
 *
 * Genérica de propósito: a lista de conversas e o resumo por assuntos usam a
 * mesma grelha, para se comportarem do mesmo modo (ordenar clicando no
 * cabeçalho, agrupar por qualquer coluna, escolher quantas linhas por página).
 */
export function Grelha<T>({
  linhas,
  colunas,
  chaveLinha,
  agrupaveis = [],
  porPaginaInicial = 10,
  textoVazio = 'Sem dados.',
}: Props<T>) {
  const [ordenarPor, setOrdenarPor] = useState<string>(colunas[0]?.chave ?? '');
  const [direcao, setDirecao] = useState<Direcao>('desc');
  const [agruparPor, setAgruparPor] = useState<string>('');
  const [filtro, setFiltro] = useState('');
  const [pagina, setPagina] = useState(0);
  const [porPagina, setPorPagina] = useState<number>(porPaginaInicial);
  const [fechados, setFechados] = useState<Record<string, boolean>>({});

  const colunaOrdenar = colunas.find((c) => c.chave === ordenarPor);
  const colunaAgrupar = colunas.find((c) => c.chave === agruparPor);

  const filtradas = useMemo(() => {
    const termo = filtro.trim().toLowerCase();
    if (!termo) return linhas;
    return linhas.filter((linha) =>
      colunas.some((c) => String(c.valor(linha) ?? '').toLowerCase().includes(termo)),
    );
  }, [linhas, colunas, filtro]);

  const ordenadas = useMemo(() => {
    if (!colunaOrdenar) return filtradas;
    const copia = [...filtradas];
    copia.sort((a, b) => {
      const r = comparar(colunaOrdenar.valor(a), colunaOrdenar.valor(b));
      return direcao === 'asc' ? r : -r;
    });
    return copia;
  }, [filtradas, colunaOrdenar, direcao]);

  // Agrupamento: mantém a ordem das linhas dentro de cada grupo.
  const grupos = useMemo(() => {
    if (!colunaAgrupar) return null;
    const mapa = new Map<string, T[]>();
    for (const linha of ordenadas) {
      const chave = String(colunaAgrupar.valor(linha) ?? '(sem valor)');
      const lista = mapa.get(chave);
      if (lista) lista.push(linha);
      else mapa.set(chave, [linha]);
    }
    return [...mapa.entries()].sort((a, b) => comparar(a[0], b[0]));
  }, [ordenadas, colunaAgrupar]);

  const totalPaginas = Math.max(1, Math.ceil(ordenadas.length / porPagina));
  const paginaAtual = Math.min(pagina, totalPaginas - 1);
  const visiveis = agruparPor
    ? ordenadas // com agrupamento mostra tudo (os grupos já organizam)
    : ordenadas.slice(paginaAtual * porPagina, paginaAtual * porPagina + porPagina);

  const alternarOrdem = (chave: string) => {
    if (chave === ordenarPor) setDirecao(direcao === 'asc' ? 'desc' : 'asc');
    else {
      setOrdenarPor(chave);
      setDirecao('asc');
    }
    setPagina(0);
  };

  const desenharLinha = (linha: T) => (
    <tr key={chaveLinha(linha)}>
      {colunas.map((c) => (
        <td key={c.chave}>{c.render ? c.render(linha) : (c.valor(linha) ?? '—')}</td>
      ))}
    </tr>
  );

  return (
    <section>
      <div className="filtros">
        <input
          placeholder="Pesquisar…"
          value={filtro}
          onChange={(e) => {
            setFiltro(e.target.value);
            setPagina(0);
          }}
          style={{ minWidth: 200 }}
        />
        {agrupaveis.length > 0 && (
          <>
            <label htmlFor="agrupar">Agrupar por</label>
            <select
              id="agrupar"
              value={agruparPor}
              onChange={(e) => {
                setAgruparPor(e.target.value);
                setPagina(0);
              }}
            >
              <option value="">(sem agrupamento)</option>
              {colunas
                .filter((c) => agrupaveis.includes(c.chave))
                .map((c) => (
                  <option key={c.chave} value={c.chave}>
                    {c.titulo}
                  </option>
                ))}
            </select>
          </>
        )}
        <label htmlFor="por-pagina">Por página</label>
        <select
          id="por-pagina"
          value={porPagina}
          onChange={(e) => {
            setPorPagina(Number(e.target.value));
            setPagina(0);
          }}
        >
          {[10, 25, 50, 100].map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
        {(filtro || agruparPor || ordenarPor !== colunas[0]?.chave) && (
          <button
            onClick={() => {
              setFiltro('');
              setAgruparPor('');
              setOrdenarPor(colunas[0]?.chave ?? '');
              setPagina(0);
            }}
          >
            Limpar
          </button>
        )}
        <span className="rodape">
          {ordenadas.length} de {linhas.length} linha(s)
          {agruparPor && grupos ? ` · ${grupos.length} grupo(s)` : ''}
        </span>
      </div>

      {ordenadas.length === 0 ? (
        <p className="vazio">{textoVazio}</p>
      ) : (
        <table>
          <thead>
            <tr>
              {colunas.map((c) => (
                <th
                  key={c.chave}
                  onClick={() => alternarOrdem(c.chave)}
                  style={{ cursor: 'pointer', userSelect: 'none', whiteSpace: 'nowrap' }}
                  title="Clique para ordenar"
                >
                  {c.titulo}
                  {ordenarPor === c.chave ? (direcao === 'asc' ? ' ▲' : ' ▼') : ''}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {agruparPor && grupos
              ? grupos.map(([nome, itens]) => (
                  <Fragment key={`g-${nome}`}>
                    <tr style={{ background: '#f4f4f5' }}>
                      <td colSpan={colunas.length}>
                        <button
                          className="ligacao"
                          onClick={() => setFechados({ ...fechados, [nome]: !fechados[nome] })}
                        >
                          {fechados[nome] ? '▸' : '▾'} {nome}
                        </button>{' '}
                        <span className="rodape">({itens.length})</span>
                      </td>
                    </tr>
                    {!fechados[nome] && itens.map(desenharLinha)}
                  </Fragment>
                ))
              : visiveis.map(desenharLinha)}
          </tbody>
        </table>
      )}

      {!agruparPor && totalPaginas > 1 && (
        <div className="filtros" style={{ marginTop: 10 }}>
          <button onClick={() => setPagina(0)} disabled={paginaAtual === 0}>
            « Primeira
          </button>
          <button onClick={() => setPagina(paginaAtual - 1)} disabled={paginaAtual === 0}>
            Anterior
          </button>
          <span className="rodape">
            Página {paginaAtual + 1} de {totalPaginas}
          </span>
          <button onClick={() => setPagina(paginaAtual + 1)} disabled={paginaAtual >= totalPaginas - 1}>
            Seguinte
          </button>
          <button onClick={() => setPagina(totalPaginas - 1)} disabled={paginaAtual >= totalPaginas - 1}>
            Última »
          </button>
        </div>
      )}
    </section>
  );
}
