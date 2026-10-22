"""Fase 5 — gerar rascunhos e relatórios de alterações. Nunca envia nada."""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..ai.drafting import SYSTEM_PROMPT_DRAFT, build_draft_prompt, validate_draft
from ..ai.validator import AnalysisError, extract_json
from ..models import AuditLog, Conversation, Message
from ..models_analysis import AiAnalysis
from ..models_drafting import DRAFT_MODES, ReplyDraft


def gerar_rascunho(
    db: Session,
    conversation_id: int,
    provider,
    modo: str = 'objetivo',
    instrucoes: str | None = None,
    model_name: str = 'desconhecido',
) -> dict:
    if modo not in DRAFT_MODES:
        return {'ok': False, 'error': f'Modo inválido. Use um de: {", ".join(DRAFT_MODES)}'}

    conversa = db.get(Conversation, conversation_id)
    if conversa is None:
        return {'ok': False, 'error': 'Conversa não encontrada.'}

    mensagens = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.received_at.asc().nullslast(), Message.id.asc())
        .limit(40)
    ).all()
    if not mensagens:
        return {'ok': False, 'error': 'Conversa sem mensagens.'}

    contexto = [
        {
            'direction': m.direction,
            'sender': m.sender,
            'subject': m.subject,
            'body': m.body,
            'received_at': m.received_at.isoformat() if m.received_at else None,
        }
        for m in mensagens
    ]

    try:
        bruto = provider.classificar(SYSTEM_PROMPT_DRAFT, build_draft_prompt(contexto, modo, instrucoes))
        dados = validate_draft(extract_json(bruto), modo)
    except (AnalysisError, ValueError) as exc:
        db.add(AuditLog(action='draft_invalid', entity='conversation', entity_id=str(conversation_id), details=str(exc)))
        db.commit()
        return {'ok': False, 'error': f'Rascunho inválido: {exc}'}

    rascunho = ReplyDraft(
        conversation_id=conversation_id,
        mode=modo,
        subject=dados['subject'],
        body=dados['body'],
        facts_used='; '.join(dados['facts_used']) or None,
        model=model_name,
        status='rascunho',
    )
    db.add(rascunho)
    db.add(AuditLog(action='draft_created', entity='conversation', entity_id=str(conversation_id),
                    details=f'modo={modo} modelo={model_name}'))
    db.commit()

    return {
        'ok': True,
        'draft_id': rascunho.id,
        'mode': modo,
        'subject': dados['subject'],
        'body': dados['body'],
        'facts_used': dados['facts_used'],
        'open_questions': dados['open_questions'],
        'status': 'rascunho',
        'aviso': 'Rascunho para revisão humana. Nada é enviado pelo MailPilot.',
    }


def marcar_revisto(db: Session, draft_id: int, reviewed_by: str, descartar: bool = False) -> dict:
    rascunho = db.get(ReplyDraft, draft_id)
    if rascunho is None:
        return {'ok': False, 'error': 'Rascunho não encontrado.'}
    rascunho.status = 'descartado' if descartar else 'revisto'
    rascunho.reviewed_by = reviewed_by
    db.add(AuditLog(action='draft_discarded' if descartar else 'draft_reviewed',
                    entity='reply_draft', entity_id=str(draft_id), details=f'por {reviewed_by}'))
    db.commit()
    return {'ok': True, 'draft_id': draft_id, 'status': rascunho.status}


def relatorio_alteracoes(db: Session, horas: int = 24) -> dict:
    """Pendências que mudaram desde a última janela (o relatório diário do documento)."""
    desde = datetime.utcnow() - timedelta(hours=horas)
    linhas = db.execute(
        select(AiAnalysis.state, func.count(AiAnalysis.id))
        .where(AiAnalysis.created_at >= desde)
        .group_by(AiAnalysis.state)
    ).all()
    mudancas = {estado: count for estado, count in linhas}

    recentes = db.scalars(
        select(AiAnalysis).where(AiAnalysis.created_at >= desde).order_by(AiAnalysis.id.desc()).limit(50)
    ).all()

    return {
        'janela_horas': horas,
        'desde': desde.isoformat(),
        'por_estado': mudancas,
        'total_reanalises': sum(mudancas.values()),
        'detalhe': [
            {
                'conversation_id': a.conversation_id,
                'state': a.state,
                'confidence': a.confidence,
                'created_at': a.created_at.isoformat() if a.created_at else None,
            }
            for a in recentes
        ],
    }
