"""Resumo por assunto e remetentes — o "quem" que faltava na lista.

Juntar as conversas por assunto é o que dá ao utilizador a visão de topo que
não existe no Outlook: quantos fios diferentes existem sobre o mesmo tema, quem
os escreve e quantos ainda exigem ação.
"""

import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Conversation, Message

# Prefixos de resposta/reenvio que não fazem parte do assunto: "Re:", "RE:",
# "Fwd:", "FW:", "Enc:", "Res:" — repetidos ("Re: RE: Fwd: ...").
_PREFIXO = re.compile(r'^\s*(re|res|fwd?|enc|tr)\s*(\[\d+\])?\s*:\s*', re.IGNORECASE)


def normalizar_assunto(assunto: str | None) -> str:
    """Devolve o assunto sem prefixos de resposta, para agrupar o mesmo tema."""
    texto = (assunto or '').strip()
    anterior = None
    while texto != anterior:
        anterior = texto
        texto = _PREFIXO.sub('', texto).strip()
    return texto or '(sem assunto)'


def _remetentes(db: Session, ids: list[int]) -> dict[int, dict]:
    """Remetente da última mensagem e da última recebida, por conversa (uma query)."""
    if not ids:
        return {}
    linhas = db.scalars(
        select(Message).where(Message.conversation_id.in_(ids)).order_by(Message.id.asc())
    ).all()
    resumo: dict[int, dict] = {}
    for m in linhas:
        estado = resumo.setdefault(m.conversation_id, {'ultimo': None, 'ultima_recebida': None, 'por_ler': 0})
        estado['ultimo'] = {'sender': m.sender, 'direction': m.direction}
        if m.direction != 'out':
            estado['ultima_recebida'] = {'sender': m.sender, 'direction': m.direction}
        if m.is_read is False:
            estado['por_ler'] += 1
    return resumo


def remetentes_por_conversa(db: Session, ids: list[int]) -> dict[int, dict]:
    """Forma pública, já achatada, para a listagem de conversas."""
    bruto = _remetentes(db, ids)
    saida: dict[int, dict] = {}
    for cid, dados in bruto.items():
        contraparte = dados['ultima_recebida'] or dados['ultimo'] or {}
        saida[cid] = {
            'sender': contraparte.get('sender'),
            'last_sender': (dados['ultimo'] or {}).get('sender'),
            'last_direction': (dados['ultimo'] or {}).get('direction'),
            'unread': dados['por_ler'],
        }
    return saida


def resumo_por_assunto(db: Session, limite: int = 50) -> dict:
    """Agrupa as conversas pelo tema (assunto limpo de prefixos)."""
    conversas = db.scalars(select(Conversation)).all()
    remetentes = _remetentes(db, [c.id for c in conversas])

    grupos: dict[str, dict] = {}
    for c in conversas:
        chave = normalizar_assunto(c.subject)
        dados = remetentes.get(c.id, {})
        contraparte = (dados.get('ultima_recebida') or dados.get('ultimo') or {}).get('sender')
        grupo = grupos.setdefault(
            chave,
            {
                'assunto': chave,
                'variantes': set(),
                'conversas': 0,
                'mensagens': 0,
                'por_ler': 0,
                'estados': {},
                'remetentes': set(),
                'ultima': None,
                'conversation_ids': [],
            },
        )
        if c.subject and c.subject.strip() != chave:
            grupo['variantes'].add(c.subject.strip()[:200])
        grupo['conversas'] += 1
        grupo['mensagens'] += c.message_count or 0
        grupo['por_ler'] += dados.get('por_ler', 0)
        grupo['estados'][c.state] = grupo['estados'].get(c.state, 0) + 1
        if contraparte:
            grupo['remetentes'].add(contraparte)
        grupo['conversation_ids'].append(c.id)
        if c.last_message_at and (grupo['ultima'] is None or c.last_message_at > grupo['ultima']):
            grupo['ultima'] = c.last_message_at

    itens = []
    for grupo in grupos.values():
        estados = grupo['estados']
        # O estado do tema é o mais exigente dos fios que o compõem.
        for candidato in ('Preciso responder', 'Preciso executar tarefa', 'Atrasado', 'Aguardo resposta de terceiros',
                          'Em análise', 'Acompanhar', 'Informativo', 'Resolvido', 'Indeterminado'):
            if candidato in estados:
                principal = candidato
                break
        else:  # pragma: no cover
            principal = 'Indeterminado'
        itens.append(
            {
                'assunto': grupo['assunto'],
                'variantes': sorted(grupo['variantes']),
                'conversas': grupo['conversas'],
                'mensagens': grupo['mensagens'],
                'por_ler': grupo['por_ler'],
                'estado': principal,
                'estados': estados,
                'remetentes': sorted(grupo['remetentes']),
                'ultima': grupo['ultima'].isoformat() if grupo['ultima'] else None,
                'conversation_ids': sorted(grupo['conversation_ids']),
            }
        )

    itens.sort(key=lambda i: (i['ultima'] is None, i['ultima']), reverse=True)
    return {'total_temas': len(itens), 'total_conversas': len(conversas), 'items': itens[:limite]}
