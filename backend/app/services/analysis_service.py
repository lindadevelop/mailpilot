"""Fase 2 — correr o classificador e guardar o resultado com evidências.

Decisões importantes:
  * **incremental**: só se analisam conversas com mensagens novas desde a última
    análise (`analysed_until_message_id`);
  * **as correções manuais mandam**: uma conversa com correção ativa não é
    reclassificada pela IA;
  * uma resposta inválida da IA **não** é guardada e o motivo fica registado.
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..ai.prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_conversation_prompt
from ..ai.validator import AnalysisError, extract_json, validate_analysis
from ..models import AuditLog, Conversation, Message
from ..models_analysis import AiAnalysis, AiAnalysisEvidence, ManualCorrection


class Provider:
    """Interface mínima: permite testar sem Ollama."""

    def classificar(self, system_prompt: str, user_prompt: str) -> str:  # pragma: no cover
        raise NotImplementedError


def _mensagens_da_conversa(db: Session, conversation_id: int) -> list[dict]:
    linhas = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.received_at.asc().nullslast(), Message.id.asc())
    ).all()
    return [
        {
            'id': m.id,
            'direction': m.direction,
            'sender': m.sender,
            'subject': m.subject,
            'body': m.body,
            'received_at': m.received_at.isoformat() if m.received_at else None,
            'sent_at': m.sent_at.isoformat() if m.sent_at else None,
        }
        for m in linhas
    ]


def conversas_a_analisar(db: Session, limite: int = 20) -> list[Conversation]:
    """Conversas com mensagens novas desde a última análise (ou nunca analisadas)."""
    candidatas = db.scalars(
        select(Conversation).order_by(
            Conversation.last_message_at.desc().nullslast(), Conversation.id.desc()
        )
    ).all()

    a_analisar: list[Conversation] = []
    for conversa in candidatas:
        ultima_mensagem = db.scalar(
            select(func.max(Message.id)).where(Message.conversation_id == conversa.id)
        )
        if ultima_mensagem is None:
            continue
        ultima_analise = db.scalar(
            select(AiAnalysis)
            .where(AiAnalysis.conversation_id == conversa.id)
            .order_by(AiAnalysis.id.desc())
        )
        if ultima_analise and (ultima_analise.analysed_until_message_id or 0) >= ultima_mensagem:
            continue
        a_analisar.append(conversa)
        if len(a_analisar) >= limite:
            break
    return a_analisar


def correcao_manual(db: Session, conversation_id: int) -> ManualCorrection | None:
    return db.scalar(
        select(ManualCorrection).where(
            ManualCorrection.conversation_id == conversation_id,
            ManualCorrection.is_active.is_(True),
        )
    )


def analisar_conversa(db: Session, conversa: Conversation, provider: Provider, model_name: str = 'desconhecido') -> dict:
    """Analisa uma conversa. Devolve `{estado, aplicado, motivo}`."""
    correcao = correcao_manual(db, conversa.id)
    if correcao:
        # A correção humana tem precedência: a IA não a substitui em silêncio.
        return {'conversation_id': conversa.id, 'state': conversa.state, 'aplicado': False,
                'motivo': 'correcao_manual_ativa'}

    mensagens = _mensagens_da_conversa(db, conversa.id)
    if not mensagens:
        return {'conversation_id': conversa.id, 'state': conversa.state, 'aplicado': False,
                'motivo': 'sem_mensagens'}

    ids_validos = {m['id']: (m.get('body') or '') for m in mensagens}
    prompt = build_conversation_prompt(mensagens)

    try:
        bruto = provider.classificar(SYSTEM_PROMPT, prompt)
        dados = validate_analysis(extract_json(bruto), ids_validos)
    except AnalysisError as exc:
        db.add(AuditLog(action='analysis_invalid', entity='conversation', entity_id=str(conversa.id),
                        details=str(exc)))
        db.commit()
        return {'conversation_id': conversa.id, 'state': conversa.state, 'aplicado': False,
                'motivo': f'resposta_invalida: {exc}'}

    analise = AiAnalysis(
        conversation_id=conversa.id,
        account_id=conversa.account_id,
        state=dados['state'],
        reason=dados['reason'],
        confidence=dados['confidence'],
        deadline_text=dados['deadline_text'],
        commitments='; '.join(dados['commitments']) or None,
        model=model_name,
        prompt_version=PROMPT_VERSION,
        analysed_until_message_id=max(ids_validos),
        raw_response=bruto[:4000],
    )
    db.add(analise)
    db.flush()

    for ev in dados['evidence']:
        db.add(AiAnalysisEvidence(analysis_id=analise.id, message_id=ev['message_id'], quote=ev['quote']))

    estado_anterior = conversa.state
    conversa.state = dados['state']
    db.add(AuditLog(action='analysis_run', entity='conversation', entity_id=str(conversa.id),
                    details=f'{estado_anterior} -> {dados["state"]} (confianca {dados["confidence"]})'))
    db.commit()

    return {
        'conversation_id': conversa.id,
        'state': dados['state'],
        'state_before': estado_anterior,
        'confidence': dados['confidence'],
        'aplicado': True,
        'motivo': None,
    }


def run_analysis(db: Session, provider: Provider, limite: int = 20, model_name: str = 'desconhecido') -> dict:
    resultados = [analisar_conversa(db, c, provider, model_name) for c in conversas_a_analisar(db, limite)]
    return {
        'analisadas': sum(1 for r in resultados if r['aplicado']),
        'ignoradas': sum(1 for r in resultados if not r['aplicado']),
        'resultados': resultados,
    }
