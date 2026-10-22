import { useCallback, useEffect, useState } from 'react';
import { api, getApiKey, setApiKey } from './api';
import { Indicadores } from './components/Indicadores';
import { ListaConversas } from './components/ListaConversas';
import { PainelConversa } from './components/PainelConversa';
import type { Conversation, Dashboard } from './types';

export default function App() {
  const [chave, setChave] = useState(getApiKey());
  const [chaveGuardada, setChaveGuardada] = useState(getApiKey().length > 0);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [conversas, setConversas] = useState<Conversation[]>([]);
  const [total, setTotal] = useState(0);
  const [filtroEstado, setFiltroEstado] = useState('');
  const [aCarregar, setACarregar] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [aberta, setAberta] = useState<Conversation | null>(null);

  const carregar = useCallback(async () => {
    if (!chaveGuardada) return;
    setACarregar(true);
    setErro(null);
    try {
      const [dadosDashboard, pagina] = await Promise.all([
        api.dashboard(),
        api.conversas({ state: filtroEstado || undefined }),
      ]);
      setDashboard(dadosDashboard);
      setConversas(pagina.items);
      setTotal(pagina.total);
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Falha ao contactar a API.');
    } finally {
      setACarregar(false);
    }
  }, [chaveGuardada, filtroEstado]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  // Atualização parcial: recarrega os dados a cada 30 s, sem recarregar a página.
  useEffect(() => {
    if (!chaveGuardada) return;
    const id = window.setInterval(() => void carregar(), 30_000);
    return () => window.clearInterval(id);
  }, [chaveGuardada, carregar]);

  const guardarChave = () => {
    setApiKey(chave);
    setChaveGuardada(chave.trim().length > 0);
  };

  return (
    <>
      <header className="cabecalho">
        <div>
          <h1>MailPilot AI</h1>
          <div className="sub">O que exige atenção agora — sem substituir o Outlook.</div>
        </div>
        <span className="espaco" />
        <label htmlFor="chave">Chave da API</label>
        <input
          id="chave"
          type="password"
          placeholder="X-API-Key"
          value={chave}
          onChange={(e) => setChave(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && guardarChave()}
        />
        <button className="primario" onClick={guardarChave}>
          Guardar
        </button>
        <button onClick={() => void carregar()} disabled={!chaveGuardada || aCarregar}>
          Atualizar
        </button>
      </header>

      <main className="conteudo">
        {!chaveGuardada && (
          <p className="vazio">
            Indique a chave da API (a mesma <code>API_KEY</code> do <code>.env</code> do backend) para ver as
            pendências. A chave fica guardada apenas neste browser.
          </p>
        )}

        {erro && <div className="erro">{erro}</div>}

        {chaveGuardada && (
          <>
            <Indicadores dados={dashboard} />
            {aberta && <PainelConversa conversa={aberta} onFechar={() => setAberta(null)} />}
            <ListaConversas
              conversas={conversas}
              total={total}
              aCarregar={aCarregar}
              filtroEstado={filtroEstado}
              onFiltroEstado={setFiltroEstado}
              onAbrir={(id) => setAberta(conversas.find((c) => c.id === id) ?? null)}
            />
            <p className="rodape">
              Fase 1 · classificação por IA (Ollama), resumo e ações chegam na Fase 2.
            </p>
          </>
        )}
      </main>
    </>
  );
}
