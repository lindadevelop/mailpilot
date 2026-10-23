import { useCallback, useEffect, useState } from 'react';
import { api } from '../api';
import { DRAFT_MODES, type Analysis, type Conversation, type Draft } from '../types';

interface Props {
  conversa: Conversation;
  onFechar: () => void;
}

/**
 * Detalhe da conversa: estado classificado pela IA **com as evidências que o
 * sustentam** e sugestões de resposta em quatro modos. Nada é enviado daqui — o
 * rascunho serve para revisão humana, como o documento técnico exige.
 */
export function PainelConversa({ conversa, onFechar }: Props) {
  const [analise, setAnalise] = useState<Analysis | null>(null);
  const [rascunhos, setRascunhos] = useState<Draft[]>([]);
  const [modo, setModo] = useState<string>('objetivo');
  const [instrucoes, setInstrucoes] = useState('');
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  const carregar = useCallback(async () => {
    setErro(null);
    try {
      const [dadosAnalise, listaRascunhos] = await Promise.all([
        api.analise(conversa.id),
        api.rascunhos(conversa.id),
      ]);
      setAnalise(dadosAnalise.analysis);
      setRascunhos(listaRascunhos.items);
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Falha ao carregar a análise.');
    }
  }, [conversa.id]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  const gerar = async () => {
    setOcupado(true);
    setErro(null);
    setAviso(null);
    try {
      const resultado = await api.gerarRascunho(conversa.id, modo, instrucoes || undefined);
      setAviso(resultado.aviso);
      setInstrucoes('');
      await carregar();
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Falha ao gerar o rascunho.');
    } finally {
      setOcupado(false);
    }
  };

  const rever = async (draftId: number, descartar: boolean) => {
    setOcupado(true);
    setErro(null);
    try {
      await api.reverRascunho(draftId, 'utilizador-local', descartar);
      await carregar();
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Falha ao rever o rascunho.');
    } finally {
      setOcupado(false);
    }
  };

  return (
    <div className="cartao" style={{ marginBottom: 16 }}>
      <div className="filtros">
        <strong>{conversa.subject ?? '(sem assunto)'}</strong>
        <span className="etiqueta">{conversa.state}</span>
        <span style={{ flex: 1 }} />
        <button onClick={onFechar}>Fechar</button>
      </div>

      <p className="rodape">
        {conversa.message_count} mensagem(ns) · última:{' '}
        {conversa.last_message_at ? new Date(conversa.last_message_at).toLocaleString('pt-PT') : '—'}
      </p>

      {erro && <div className="erro" style={{ marginTop: 12 }}>{erro}</div>}

      <h3 style={{ fontSize: 14, marginTop: 16, marginBottom: 6 }}>Análise da IA</h3>
      {!analise ? (
        <p className="rodape">
          Sem análise para esta conversa. Corra a classificação (a API precisa do Ollama a correr) para o
          estado deixar de ser «Indeterminado».
        </p>
      ) : (
        <>
          <p className="rodape">
            <strong>{analise.state}</strong> · confiança {analise.confidence ?? '—'}
            {analise.deadline_text ? ` · prazo: ${analise.deadline_text}` : ''}
            {analise.model ? ` · modelo: ${analise.model}` : ''}
          </p>
          {analise.reason && <p className="rodape">Motivo: {analise.reason}</p>}
          {analise.evidence.length > 0 && (
            <ul className="rodape" style={{ paddingLeft: 18 }}>
              {analise.evidence.map((e, i) => (
                <li key={`${e.message_id}-${i}`}>
                  «{e.quote}» <span style={{ opacity: 0.7 }}>(mensagem {e.message_id})</span>
                </li>
              ))}
            </ul>
          )}
        </>
      )}

      <h3 style={{ fontSize: 14, marginTop: 16, marginBottom: 6 }}>Sugerir resposta</h3>
      <div className="filtros">
        <label htmlFor="modo">Modo</label>
        <select id="modo" value={modo} onChange={(e) => setModo(e.target.value)}>
          {DRAFT_MODES.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
        <input
          style={{ minWidth: 240, flex: 1 }}
          placeholder="Indicações (opcional): ex. referir prazo de entrega"
          value={instrucoes}
          onChange={(e) => setInstrucoes(e.target.value)}
        />
        <button className="primario" onClick={() => void gerar()} disabled={ocupado}>
          {ocupado ? 'A gerar…' : 'Gerar rascunho'}
        </button>
      </div>
      <p className="rodape">
        O MailPilot <strong>não envia</strong> emails: o rascunho fica para revisão. O que não existir na
        conversa aparece como marcador (ex.: [CONFIRMAR: prazo]) em vez de ser inventado.
      </p>
      {aviso && <p className="rodape" style={{ color: '#166534' }}>{aviso}</p>}

      {rascunhos.map((r) => (
        <div key={r.id} className="cartao" style={{ marginTop: 10 }}>
          <p className="rodape">
            {r.mode} · <strong>{r.status}</strong> ·{' '}
            {r.created_at ? new Date(r.created_at).toLocaleString('pt-PT') : '—'}
          </p>
          {r.subject && <p style={{ margin: '6px 0 4px' }}><strong>{r.subject}</strong></p>}
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: 13, margin: 0 }}>{r.body}</pre>
          {r.status === 'rascunho' && (
            <div className="filtros" style={{ marginTop: 8 }}>
              <button onClick={() => void rever(r.id, false)} disabled={ocupado}>
                Marcar como revisto
              </button>
              <button onClick={() => void rever(r.id, true)} disabled={ocupado}>
                Descartar
              </button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
