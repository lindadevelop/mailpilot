import type { Dashboard } from '../types';

interface Props {
  dados: Dashboard | null;
}

/** Página inicial orientada à ação: o que exige atenção agora, não a caixa de correio. */
export function Indicadores({ dados }: Props) {
  if (!dados) return null;

  const cartoes = [
    { rotulo: 'Preciso responder', valor: dados.preciso_responder, destacado: true },
    { rotulo: 'Aguardo terceiros', valor: dados.aguardo_terceiros, destacado: true },
    { rotulo: 'Atrasados', valor: dados.atrasados, destacado: true },
    { rotulo: 'Por ler', valor: dados.unread_messages },
    { rotulo: 'Mensagens', valor: dados.total_messages },
  ];

  return (
    <div className="indicadores">
      {cartoes.map((c) => (
        <div key={c.rotulo} className={`cartao${c.destacado ? ' destacado' : ''}`}>
          <div className="rotulo">{c.rotulo}</div>
          <div className="valor">{c.valor}</div>
        </div>
      ))}
    </div>
  );
}
